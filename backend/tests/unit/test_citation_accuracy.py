"""Unit tests for citation accuracy metrics — deterministic, no LLM or DB."""

import pytest

from eval.metrics.citation_accuracy import (
    citation_precision,
    citation_recall,
    evaluate_batch,
    parse_citations,
)

_RETRIEVED = {
    "Grundlagen des Marketing, 1 Marketing-Mix",
    "Grundlagen des Marketing, 1.1 Produktpolitik",
    "Transaktionskostentheorie, 1.2 Spezifität",
}


class TestParseCitations:
    def test_single_citation(self) -> None:
        text = "Der Marketing-Mix *(Quelle: Grundlagen des Marketing, 1 Marketing-Mix)*."
        assert parse_citations(text) == ["Grundlagen des Marketing, 1 Marketing-Mix"]

    def test_multiple_citations_separate(self) -> None:
        text = (
            "*(Quelle: Grundlagen des Marketing, 1 Marketing-Mix)* "
            "*(Quelle: Transaktionskostentheorie, 1.2 Spezifität)*"
        )
        result = parse_citations(text)
        assert len(result) == 2
        assert "Grundlagen des Marketing, 1 Marketing-Mix" in result
        assert "Transaktionskostentheorie, 1.2 Spezifität" in result

    def test_semicolon_separated_in_one_pattern(self) -> None:
        text = (
            "*(Quelle: Grundlagen des Marketing, 1 Marketing-Mix;"
            " Transaktionskostentheorie, 1.2 Spezifität)*"
        )
        result = parse_citations(text)
        assert "Grundlagen des Marketing, 1 Marketing-Mix" in result
        assert "Transaktionskostentheorie, 1.2 Spezifität" in result

    def test_web_citations_excluded(self) -> None:
        text = "*(Quelle: Web – Some Site, https://example.com)*"
        assert parse_citations(text) == []

    def test_no_citations(self) -> None:
        assert parse_citations("Keine Quellenangaben in diesem Text.") == []

    def test_empty_string(self) -> None:
        assert parse_citations("") == []


class TestCitationPrecision:
    def test_perfect_precision(self) -> None:
        text = "Laut Studienmaterial *(Quelle: Grundlagen des Marketing, 1 Marketing-Mix)*."
        assert citation_precision(text, _RETRIEVED) == 1.0

    def test_fully_hallucinated_source(self) -> None:
        text = "*(Quelle: Erfundenes Buch, Kapitel 99)*"
        assert citation_precision(text, _RETRIEVED) == 0.0

    def test_mixed_half_hallucinated(self) -> None:
        text = (
            "*(Quelle: Grundlagen des Marketing, 1 Marketing-Mix)* "
            "*(Quelle: Erfundenes Buch, Kapitel 99)*"
        )
        assert citation_precision(text, _RETRIEVED) == pytest.approx(0.5)

    def test_no_citations_returns_one(self) -> None:
        # Vacuously precise — model withheld citation when none were retrieved
        assert citation_precision("Kein Beleg nötig.", _RETRIEVED) == 1.0

    def test_prefix_match_counts_as_hit(self) -> None:
        # LLM may trim label; prefix match should still count
        text = "*(Quelle: Grundlagen des Marketing)*"
        assert citation_precision(text, _RETRIEVED) == 1.0


class TestCitationRecall:
    def test_full_recall(self) -> None:
        expected = ["Grundlagen des Marketing, 1 Marketing-Mix"]
        text = "*(Quelle: Grundlagen des Marketing, 1 Marketing-Mix)*"
        assert citation_recall(text, expected) == 1.0

    def test_zero_recall(self) -> None:
        expected = ["Grundlagen des Marketing, 1 Marketing-Mix"]
        assert citation_recall("Keine Quellenangabe.", expected) == 0.0

    def test_empty_expected_returns_one(self) -> None:
        assert citation_recall("Beliebiger Text", []) == 1.0

    def test_partial_recall(self) -> None:
        expected = [
            "Grundlagen des Marketing, 1 Marketing-Mix",
            "Grundlagen des Marketing, 1.1 Produktpolitik",
        ]
        text = "*(Quelle: Grundlagen des Marketing, 1 Marketing-Mix)*"
        assert citation_recall(text, expected) == pytest.approx(0.5)


class TestEvaluateBatch:
    def test_empty_batch(self) -> None:
        result = evaluate_batch([])
        assert result["precision"] == 1.0
        assert result["recall"] == 1.0
        assert result["n"] == 0

    def test_perfect_batch(self) -> None:
        items = [
            {
                "response": "*(Quelle: Grundlagen des Marketing, 1 Marketing-Mix)*",
                "retrieved_labels": ["Grundlagen des Marketing, 1 Marketing-Mix"],
                "expected_labels": ["Grundlagen des Marketing, 1 Marketing-Mix"],
            }
        ]
        result = evaluate_batch(items)
        assert result["precision"] == 1.0
        assert result["recall"] == 1.0
        assert result["n"] == 1

    def test_hallucinated_source_lowers_precision(self) -> None:
        items = [
            {
                "response": "*(Quelle: Erfundenes Buch, Kap 1)*",
                "retrieved_labels": ["Grundlagen des Marketing, 1 Marketing-Mix"],
                "expected_labels": [],
            }
        ]
        result = evaluate_batch(items)
        assert result["precision"] == 0.0

    def test_missing_citation_lowers_recall(self) -> None:
        items = [
            {
                "response": "Keine Quellen genannt.",
                "retrieved_labels": ["Grundlagen des Marketing, 1 Marketing-Mix"],
                "expected_labels": ["Grundlagen des Marketing, 1 Marketing-Mix"],
            }
        ]
        result = evaluate_batch(items)
        assert result["recall"] == 0.0

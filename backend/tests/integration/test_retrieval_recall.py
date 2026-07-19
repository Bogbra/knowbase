"""Integration tests — retrieval Recall@8 against the eval corpus.

Automatically skipped when OPENAI_API_KEY is not set.
Requires a live PostgreSQL instance with pgvector and the eval corpus ingested
via the session-scoped corpus_workspace_id fixture (see conftest.py).
"""

from __future__ import annotations

import json
from pathlib import Path

from eval.metrics.retrieval_recall import evaluate_recall_dataset, recall_at_k

GOLDEN_PATH = Path(__file__).parent.parent.parent / "eval" / "golden" / "questions.jsonl"
BASELINE_PATH = Path(__file__).parent.parent.parent / "eval" / "baselines" / "scores.json"


def _load_golden() -> list[dict[str, object]]:
    with GOLDEN_PATH.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def _load_baseline() -> dict[str, object]:
    with BASELINE_PATH.open() as f:
        return json.load(f)


class TestRetrievalRecall:
    async def test_recall_at_8_meets_baseline(
        self, db_session: object, corpus_workspace_id: str
    ) -> None:
        """Recall@8 must not drop below baseline − tolerance."""
        questions = _load_golden()
        baseline = _load_baseline()
        bl = baseline["recall_at_8"]
        assert isinstance(bl, dict)
        threshold = float(bl["value"]) - float(bl["tolerance"])

        result = await evaluate_recall_dataset(
            questions=questions,
            session=db_session,  # type: ignore[arg-type]
            workspace_id=corpus_workspace_id,
            k=8,
        )

        recall = float(result["recall_at_k"])
        assert recall >= threshold, (
            f"Recall@8 {recall:.3f} dropped below threshold {threshold:.3f}. "
            f"Hits: {result['n_hits']}/{result['n_evaluated']}. "
            f"Missed: {result['missed']}"
        )

    async def test_marketing_mix_retrieved(
        self, db_session: object, corpus_workspace_id: str
    ) -> None:
        """Spot-check: 'Was ist der Marketing-Mix?' retrieves the right chapter."""
        hit = await recall_at_k(
            question="Was versteht man unter dem Marketing-Mix?",
            expected_doc="Grundlagen des Marketing",
            expected_chapter="1 Marketing-Mix",
            workspace_id=corpus_workspace_id,
            session=db_session,  # type: ignore[arg-type]
            k=8,
        )
        assert hit, "Marketing-Mix definition not found in top-8 results"

    async def test_hold_up_problem_retrieved(
        self, db_session: object, corpus_workspace_id: str
    ) -> None:
        """Spot-check: 'Hold-up-Problem' retrieves the Spezifität chapter."""
        hit = await recall_at_k(
            question="Was ist das Hold-up-Problem?",
            expected_doc="Transaktionskostentheorie",
            expected_chapter="1.2 Spezifität",
            workspace_id=corpus_workspace_id,
            session=db_session,  # type: ignore[arg-type]
            k=8,
        )
        assert hit, "Hold-up-Problem not found in top-8 results"

    async def test_matrix_organisation_retrieved(
        self, db_session: object, corpus_workspace_id: str
    ) -> None:
        """Spot-check: Matrixorganisation question retrieves correct chapter."""
        hit = await recall_at_k(
            question="Was kennzeichnet die Matrixorganisation und was ist das Zwei-Linien-Prinzip?",
            expected_doc="Organisationstheorie",
            expected_chapter="1.3 Matrixorganisation",
            workspace_id=corpus_workspace_id,
            session=db_session,  # type: ignore[arg-type]
            k=8,
        )
        assert hit, "Matrixorganisation not found in top-8 results"

    async def test_ood_questions_excluded_from_metric(self) -> None:
        """OOD questions (expected_no_source=True) must not contribute to recall."""
        questions = _load_golden()
        ood = [q for q in questions if q.get("expected_no_source")]
        in_scope = [
            q for q in questions if not q.get("expected_no_source") and q.get("expected_doc")
        ]
        assert len(ood) >= 3, "Golden dataset should have at least 3 OOD questions"
        assert len(in_scope) >= 30, "Golden dataset should have at least 30 in-scope questions"

"""Citation accuracy — deterministic, no LLM or DB required.

Given a model response and a set of valid source labels (from retrieved chunks),
two metrics are computed:

  precision   fraction of cited labels that exist in retrieved_labels
              (measures hallucination of source references)

  recall      fraction of expected_labels that appear in the response citations
              (measures whether expected sources were actually cited)

Source labels follow the format produced by the retrieval node:
  "{document_name}, {chapter}"  or  "{document_name}" when chapter is absent.

Web citations (*(Quelle: Web – ...)*) are excluded from precision / recall
because they have a different validation path.
"""

from __future__ import annotations

import re

_CITATION_RE = re.compile(r"\*\(Quelle:\s*([^)]+)\)\*")


def parse_citations(text: str) -> list[str]:
    """Return source labels extracted from *(Quelle: SOURCE)* patterns in text.

    Splits on semicolons to handle multi-source citations.
    Excludes web citations that start with 'Web –'.
    """
    labels: list[str] = []
    for match in _CITATION_RE.finditer(text):
        for part in match.group(1).split(";"):
            label = part.strip()
            if label and not label.startswith("Web –"):
                labels.append(label)
    return labels


def _label_matches(cited: str, valid: str) -> bool:
    """True when cited and valid refer to the same source.

    Allows prefix matching in both directions to handle LLM label trimming.
    """
    return cited == valid or cited.startswith(valid) or valid.startswith(cited)


def citation_precision(response: str, retrieved_labels: set[str]) -> float:
    """Fraction of cited labels that exist in retrieved_labels.

    Returns 1.0 when no citations are present (vacuously precise — the model
    correctly withheld source references when none were retrieved).
    """
    cited = parse_citations(response)
    if not cited:
        return 1.0
    matched = sum(
        1 for label in cited if any(_label_matches(label, valid) for valid in retrieved_labels)
    )
    return matched / len(cited)


def citation_recall(response: str, expected_labels: list[str]) -> float:
    """Fraction of expected_labels that appear in the response citations.

    Returns 1.0 when expected_labels is empty.
    """
    if not expected_labels:
        return 1.0
    cited = parse_citations(response)
    matched = sum(
        1 for label in expected_labels if any(_label_matches(cited_l, label) for cited_l in cited)
    )
    return matched / len(expected_labels)


def evaluate_batch(
    responses: list[dict[str, object]],
) -> dict[str, float]:
    """Aggregate precision and recall over a batch of evaluated responses.

    Each item must contain:
      "response"         str        — model response text
      "retrieved_labels" list[str]  — source labels from the retrieved chunks
      "expected_labels"  list[str]  — expected source labels for the question

    Returns {"precision": float, "recall": float, "n": int}.
    """
    if not responses:
        return {"precision": 1.0, "recall": 1.0, "n": 0}

    precisions: list[float] = []
    recalls: list[float] = []
    for item in responses:
        response = str(item["response"])
        retrieved = {str(lbl) for lbl in item.get("retrieved_labels", [])}  # type: ignore[union-attr]
        expected = [str(lbl) for lbl in item.get("expected_labels", [])]  # type: ignore[union-attr]
        precisions.append(citation_precision(response, retrieved))
        recalls.append(citation_recall(response, expected))

    return {
        "precision": sum(precisions) / len(precisions),
        "recall": sum(recalls) / len(recalls),
        "n": len(responses),
    }

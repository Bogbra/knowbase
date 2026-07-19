"""Eval runner — measures retrieval recall against the golden dataset.

Usage (from backend/):
  uv run python -m eval.runner setup                     # ingest corpus, print workspace ID
  uv run python -m eval.runner recall --workspace-id ID  # compute Recall@8, print scores
  uv run python -m eval.runner check                     # compare saved scores against baselines

Environment:
  DATABASE_URL      PostgreSQL connection string (postgresql+asyncpg://...)
  OPENAI_API_KEY    Required for embedding (setup + recall commands)
  EVAL_WORKSPACE_ID Workspace to query (alternative to --workspace-id)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

GOLDEN_PATH = Path(__file__).parent / "golden" / "questions.jsonl"
BASELINE_PATH = Path(__file__).parent / "baselines" / "scores.json"
SCORES_CACHE = Path(__file__).parent / ".last_scores.json"


def _load_golden() -> list[dict[str, object]]:
    with GOLDEN_PATH.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def _load_baselines() -> dict[str, object]:
    with BASELINE_PATH.open() as f:
        return json.load(f)


async def _setup() -> None:
    """Create workspace, ingest corpus, print workspace ID."""
    from app.db.session import AsyncSessionLocal
    from eval.fixtures import create_eval_workspace, ingest_corpus

    print("Ingesting eval corpus… (this makes OpenAI embedding calls)")
    async with AsyncSessionLocal() as session:
        _, workspace = await create_eval_workspace(session)
        docs = await ingest_corpus(session, workspace.id, embed=True)
        await session.commit()

    for doc in docs:
        print(f"  ✓ {doc.name}")
    print(f"\nWorkspace ID: {workspace.id}")
    print(f"Set EVAL_WORKSPACE_ID={workspace.id} or pass --workspace-id to recall/check.")


async def _recall(workspace_id: str, k: int) -> dict[str, object]:
    """Embed all golden questions, run retrieval, compute Recall@k."""
    from app.db.session import AsyncSessionLocal
    from eval.metrics.retrieval_recall import evaluate_recall_dataset

    questions = _load_golden()
    print(f"Evaluating Recall@{k} on {len(questions)} questions…")

    async with AsyncSessionLocal() as session:
        result = await evaluate_recall_dataset(
            questions=questions,
            session=session,
            workspace_id=workspace_id,
            k=k,
        )

    pct = result["recall_at_k"] * 100  # type: ignore[operator]
    print(f"\nRecall@{k}: {pct:.1f}%  ({result['n_hits']}/{result['n_evaluated']} questions)")
    if result["missed"]:
        print(f"Missed: {', '.join(result['missed'])}")  # type: ignore[arg-type]

    SCORES_CACHE.write_text(json.dumps({"recall_at_8": result["recall_at_k"]}, indent=2))
    print(f"\nScores cached to {SCORES_CACHE}")
    return result


def _check() -> None:
    """Compare cached scores against committed baselines."""
    if not SCORES_CACHE.exists():
        print("No cached scores found. Run `recall` first.", file=sys.stderr)
        sys.exit(1)

    scores = json.loads(SCORES_CACHE.read_text())
    baselines = _load_baselines()
    failed = False

    ratchet_hints: list[str] = []

    for metric, value in scores.items():
        bl = baselines.get(metric)
        if not isinstance(bl, dict):
            continue
        baseline_val = float(bl["value"])  # type: ignore[index]
        tolerance = float(bl["tolerance"])  # type: ignore[index]
        threshold = baseline_val - tolerance
        score = float(value)  # type: ignore[arg-type]
        status = "OK" if score >= threshold else "FAIL"
        score_str = f"{score:.3f} >= {threshold:.3f}"
        meta_str = f"(baseline={baseline_val:.3f}, tol={tolerance:.3f})"
        print(f"  {status}  {metric}: {score_str} {meta_str}")
        if status == "FAIL":
            failed = True
        # Ratchet hint: score is consistently well above baseline → tolerance too loose.
        # Guideline: raise baseline to observed score, set tolerance = max(0.03, std_dev).
        if score >= baseline_val + tolerance / 2:
            suggested_tol = round(min(tolerance / 2, 0.05), 3)
            ratchet_hints.append(
                f"  ↑  {metric}: score {score:.3f} ≥ baseline+tol/2"
                f" ({baseline_val + tolerance / 2:.3f}) — ratchet baseline"
                f" to {score:.3f} with tol={suggested_tol:.3f}"
            )

    if ratchet_hints:
        print("\nRatchet suggestions (scores stable above baseline — tighten to protect):")
        for hint in ratchet_hints:
            print(hint)
        print("  → edit eval/baselines/scores.json, commit after 2–3 consistent runs.")

    if failed:
        print("\nBaseline check FAILED.", file=sys.stderr)
        sys.exit(1)
    print("\nAll baselines met.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Knowbase eval runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("setup", help="Ingest corpus into a new workspace")

    recall_p = sub.add_parser("recall", help="Compute Recall@k against golden dataset")
    recall_p.add_argument("--workspace-id", default=os.environ.get("EVAL_WORKSPACE_ID"))
    recall_p.add_argument("--k", type=int, default=8)

    sub.add_parser("check", help="Compare cached scores against baselines")

    args = parser.parse_args()

    if args.command == "setup":
        asyncio.run(_setup())
    elif args.command == "recall":
        if not args.workspace_id:
            parser.error("--workspace-id or EVAL_WORKSPACE_ID required")
        asyncio.run(_recall(args.workspace_id, args.k))
    elif args.command == "check":
        _check()


if __name__ == "__main__":
    main()

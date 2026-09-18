"""Score the 100-question dataset with a coarse Jev date label."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from time import perf_counter
from typing import Any

from dotenv import load_dotenv

from ..shared.provider import JevProvider
from .date_classification import date_question, expected_date_label
from .layer import load_semantic_layer, prepare_question, resolve_answers
from .layer_benchmark import DATASET_PATH, load_dataset, validate_dataset

SCORE_FIELDS = ("entities", "target", "metric", "date", "joint", "rule_date", "rule_joint")


def benchmark_rows() -> list[dict[str, Any]]:
    rows = load_dataset(DATASET_PATH)
    if len(rows) != 100 or len({row["question"] for row in rows}) != 100:
        raise ValueError("Expected 100 distinct questions in the benchmark dataset")
    return rows


def score(row: dict[str, Any], resolved: dict[str, Any], model_date: str) -> dict[str, bool]:
    expected_date = expected_date_label(row["period"])
    checks = {
        "entities": set(row["entities"]) == {entity["entity_id"] for entity in resolved["entities"]},
        "target": row["target"] == resolved["target_entity_id"],
        "metric": row["metric"] == resolved["metric_id"],
        "date": expected_date == model_date,
        "rule_date": expected_date == expected_date_label(resolved["period"]),
    }
    checks["joint"] = all(checks[field] for field in ("entities", "target", "metric", "date"))
    checks["rule_joint"] = all(
        checks[field] for field in ("entities", "target", "metric", "rule_date")
    )
    return checks


def counts(counter: Counter[str], total: int) -> dict[str, Any]:
    return {
        "correct": {field: counter[field] for field in SCORE_FIELDS},
        "accuracy": {field: round(counter[field] / total, 4) for field in SCORE_FIELDS},
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark coarse date labels on 100 finance questions."
    )
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--details", action="store_true", help="Include all predictions, not just misses")
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")

    load_dotenv()
    if not os.getenv("TYPESAFE_API_KEY") or os.getenv("TYPESAFE_API_KEY") == "replace_me":
        parser.error("Set TYPESAFE_API_KEY in .env before running this benchmark.")

    start = perf_counter()
    layer = load_semantic_layer()
    graph = layer["metric_graph"]
    catalog = layer["entities"]
    rows = benchmark_rows()
    validate_dataset(rows, catalog, graph)

    totals: Counter[str] = Counter()
    labels = Counter(expected_date_label(row["period"]) for row in rows)
    details = []
    call_ms = []
    model = None
    provider = JevProvider()

    for start_index in range(0, len(rows), args.batch_size):
        batch = rows[start_index:start_index + args.batch_size]
        questions: dict[str, object] = {}
        prepared = []
        for local_index, row in enumerate(batch, start=1):
            mentions, rule_period, local_questions = prepare_question(
                row["question"], graph, catalog
            )
            prepared.append((mentions, rule_period))
            for name, question in local_questions.items():
                questions[f"q{local_index}_{name}"] = question
            questions[f"q{local_index}_date"] = date_question(row["question"])

        call_start = perf_counter()
        response = provider.evaluate(
            {"semantic_layer": layer, "questions": [row["question"] for row in batch]},
            questions,
        )
        call_ms.append(round((perf_counter() - call_start) * 1000, 1))
        model = response.model

        for local_index, (row, (mentions, rule_period)) in enumerate(
            zip(batch, prepared), start=1
        ):
            answers = {"metric": response.answers[f"q{local_index}_metric"]}
            if len(mentions) > 1:
                answers["target_entity"] = response.answers[f"q{local_index}_target_entity"]
            resolved = resolve_answers(answers, mentions, rule_period, graph)
            model_date = response.answers[f"q{local_index}_date"].choice
            checks = score(row, resolved, model_date)
            totals.update(field for field, correct in checks.items() if correct)
            if args.details or not checks["joint"]:
                details.append({
                    "number": start_index + local_index,
                    "question": row["question"],
                    "expected": {
                        "entities": row["entities"],
                        "target": row["target"],
                        "metric": row["metric"],
                        "date": expected_date_label(row["period"]),
                    },
                    "predicted": {
                        "entities": [item["entity_id"] for item in resolved["entities"]],
                        "target": resolved["target_entity_id"],
                        "metric": resolved["metric_id"],
                        "date": model_date,
                        "rule_date": expected_date_label(resolved["period"]),
                    },
                    "matches": checks,
                })

    result = {
        "model": model,
        "dataset": str(DATASET_PATH),
        "question_count": len(rows),
        "date_label_distribution": dict(sorted(labels.items())),
        "overall": counts(totals, len(rows)),
        "batch_count": len(call_ms),
        "api_call_ms_by_batch": call_ms,
        "api_call_ms_total": round(sum(call_ms), 1),
        "end_to_end_in_process_ms": round((perf_counter() - start) * 1000, 1),
        "details": details,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

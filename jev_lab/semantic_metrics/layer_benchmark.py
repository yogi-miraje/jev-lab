"""Score exact entity, target, metric, period, and joint matches on a dataset."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from time import perf_counter
from typing import Any

from dotenv import load_dotenv

from ..shared.provider import JevProvider
from .layer import load_semantic_layer, prepare_question, resolve_answers
from .resolver import metric_nodes

DATASET_PATH = Path(__file__).parent / "data" / "semantic_layer_questions_100.jsonl"


def load_dataset(path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def validate_dataset(rows: list[dict[str, Any]], catalog: list[dict[str, Any]], graph: dict[str, Any]) -> None:
    if not rows:
        raise ValueError("Benchmark must contain at least one question")
    valid_entities = {row["id"] for row in catalog}
    valid_metrics = {row["id"] for row in metric_nodes(graph)}
    questions = [row["question"] for row in rows]
    if len(set(questions)) != len(questions):
        raise ValueError("Benchmark questions must be unique")
    for index, row in enumerate(rows, start=1):
        if row["metric"] not in valid_metrics:
            raise ValueError(f"Question {index} references an unknown metric ID")
        if not set(row["entities"]) <= valid_entities:
            raise ValueError(f"Question {index} references an unknown entity ID")
        if row["target"] is not None and row["target"] not in row["entities"]:
            raise ValueError(f"Question {index} target must be one of its entities")


def score_result(row: dict[str, Any], resolution: dict[str, Any]) -> dict[str, bool]:
    fields = {
        "entities": set(row["entities"]) == {item["entity_id"] for item in resolution["entities"]},
        "target": row["target"] == resolution["target_entity_id"],
        "metric": row["metric"] == resolution["metric_id"],
        "period": row["period"] == resolution["period"],
    }
    return {**fields, "joint": all(fields.values())}


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark semantic-layer resolution on a labeled dataset.")
    parser.add_argument("--details", action="store_true", help="Include every expected and predicted record")
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH, help="Labeled JSONL dataset")
    parser.add_argument("--batch-size", type=int, default=50, help="Questions per TypeSafe call (default: 50)")
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
    rows = load_dataset(args.dataset)
    validate_dataset(rows, catalog, graph)

    totals: Counter[str] = Counter()
    details = []
    question_count = 0
    batch_times_ms = []
    model_name = None
    provider = JevProvider()
    for batch_start in range(0, len(rows), args.batch_size):
        batch = rows[batch_start:batch_start + args.batch_size]
        questions: dict[str, object] = {}
        prepared = []
        for index, row in enumerate(batch, start=1):
            mentions, period, local_questions = prepare_question(row["question"], graph, catalog)
            prepared.append((mentions, period))
            for name, question in local_questions.items():
                questions[f"q{index}_{name}"] = question
        question_count += len(questions)

        api_start = perf_counter()
        response = provider.evaluate(
            {
                "semantic_layer": layer,
                "questions": [row["question"] for row in batch],
            },
            questions,
        )
        batch_times_ms.append(round((perf_counter() - api_start) * 1_000, 1))
        model_name = response.model

        for index, (row, (mentions, period)) in enumerate(zip(batch, prepared), start=1):
            answers = {"metric": response.answers[f"q{index}_metric"]}
            if len(mentions) > 1:
                answers["target_entity"] = response.answers[f"q{index}_target_entity"]
            resolution = resolve_answers(answers, mentions, period, graph)
            scores = score_result(row, resolution)
            totals.update(name for name, passed in scores.items() if passed)
            if args.details or not scores["joint"]:
                details.append(
                    {
                        "number": batch_start + index,
                        "question": row["question"],
                        "expected": {key: row[key] for key in ("entities", "target", "metric", "period")},
                        "predicted": resolution,
                        "matches": scores,
                    }
                )

    total_ms = (perf_counter() - start) * 1_000
    category_by_id = {entity["id"]: entity["category"] for entity in catalog}
    distribution = {
        "metric": dict(sorted(Counter(row["metric"] for row in rows).items())),
        "period_kind": dict(sorted(Counter(row["period"]["kind"] for row in rows).items())),
        "entity_count": dict(sorted(Counter(len(row["entities"]) for row in rows).items())),
        "entity_category_mentions": dict(sorted(Counter(
            category_by_id[entity_id]
            for row in rows for entity_id in row["entities"]
        ).items())),
        "unique_entity_ids": len({entity_id for row in rows for entity_id in row["entities"]}),
    }
    result = {
        "dataset": str(args.dataset),
        "model": model_name,
        "semantic_layer_id": layer["layer_id"],
        "semantic_graph_id": graph["graph_id"],
        "question_count": len(rows),
        "decision_question_count": question_count,
        "batch_count": len(batch_times_ms),
        "batch_size": args.batch_size,
        "distribution": distribution,
        "correct": {key: totals[key] for key in ("entities", "target", "metric", "period", "joint")},
        "accuracy": {key: round(totals[key] / len(rows), 4) for key in ("entities", "target", "metric", "period", "joint")},
        "api_call_ms_by_batch": batch_times_ms,
        "api_call_ms_total": round(sum(batch_times_ms), 1),
        "end_to_end_in_process_ms": round(total_ms, 1),
        "details": details,
    }
    print(json.dumps(result, indent=2))

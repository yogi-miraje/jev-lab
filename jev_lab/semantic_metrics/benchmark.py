from __future__ import annotations

import json
import os
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv

from ..shared.provider import JevProvider
from .resolver import load_semantic_graph, metric_question, semantic_metric_decision

QUESTIONS_PATH = Path(__file__).parent / "data" / "semantic_metric_questions_10.json"


def main() -> None:
    load_dotenv()
    if not os.getenv("TYPESAFE_API_KEY") or os.getenv("TYPESAFE_API_KEY") == "replace_me":
        raise SystemExit("Set TYPESAFE_API_KEY in .env before running this benchmark.")

    graph = load_semantic_graph()
    examples = json.loads(QUESTIONS_PATH.read_text())
    questions = {
        f"question_{number}": metric_question(example["question"], graph)
        for number, example in enumerate(examples, start=1)
    }

    start = perf_counter()
    response = JevProvider().evaluate(
        {
            "semantic_knowledge_graph": graph,
            "natural_language_questions": [example["question"] for example in examples],
        },
        questions,
    )
    elapsed_ms = (perf_counter() - start) * 1_000

    results = []
    correct = 0
    for number, example in enumerate(examples, start=1):
        resolution = semantic_metric_decision(response.answers[f"question_{number}"], graph)
        is_correct = resolution["metric_id"] == example["expected_metric_id"]
        correct += is_correct
        results.append(
            {
                "question": example["question"],
                "expected_metric_id": example["expected_metric_id"],
                "predicted_metric_id": resolution["metric_id"],
                "confidence": resolution["confidence"],
                "correct": is_correct,
            }
        )

    print(
        json.dumps(
            {
                "model": response.model,
                "semantic_graph_id": graph["graph_id"],
                "question_count": len(examples),
                "exact_metric_id_matches": correct,
                "exact_metric_id_accuracy": correct / len(examples),
                "in_process_workflow_ms": round(elapsed_ms, 1),
                "results": results,
            },
            indent=2,
        )
    )

from __future__ import annotations

import json
import os
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
from typesafe_sdk import Choice

from ..shared.provider import JevProvider
from .classifier import ENTITY_CRITERIA

DATASET_PATH = Path(__file__).parent / "data" / "financial_entities_20.json"
PROMPTS_PATH = Path(__file__).parent / "data" / "financial_prompts_20.json"


def extract_catalog_mentions(prompt: str, catalog: list[dict[str, str]]) -> list[str]:
    """Exact-name matcher; replace with an alias/ticker matcher in a real pipeline."""
    lowered = prompt.lower()
    return [row["entity"] for row in catalog if row["entity"].lower() in lowered]


def main() -> None:
    load_dotenv()
    if not os.getenv("TYPESAFE_API_KEY") or os.getenv("TYPESAFE_API_KEY") == "replace_me":
        raise SystemExit("Set TYPESAFE_API_KEY in .env before running this benchmark.")

    catalog = json.loads(DATASET_PATH.read_text())
    prompts = json.loads(PROMPTS_PATH.read_text())
    start = perf_counter()
    questions: dict[str, object] = {}
    expected_pairs: set[tuple[int, str, str]] = set()
    sources_by_question_id: dict[str, tuple[int, str]] = {}
    for prompt_number, row in enumerate(prompts, start=1):
        for expected in row["entities"]:
            expected_pairs.add((prompt_number, expected["entity"], expected["category"]))
        for entity_number, entity in enumerate(extract_catalog_mentions(row["prompt"], catalog), start=1):
            question_id = f"prompt_{prompt_number}_entity_{entity_number}"
            sources_by_question_id[question_id] = (prompt_number, entity)
            questions[question_id] = Choice(
                instructions=(
                    f"In research question {prompt_number}, classify the mentioned entity '{entity}'. "
                    "Choose its primary financial-entity category."
                ),
                criteria=ENTITY_CRITERIA,
            )
    state = {"research_questions": [row["prompt"] for row in prompts]}
    response = JevProvider().evaluate(state, questions)
    elapsed_ms = (perf_counter() - start) * 1_000

    results = []
    correct_pairs = 0
    predicted_pairs: set[tuple[int, str, str]] = set()
    for question_id, answer in response.answers.items():
        prompt_number, entity = sources_by_question_id[question_id]
        predicted_pair = (prompt_number, entity, answer.choice)
        predicted_pairs.add(predicted_pair)
        is_correct = predicted_pair in expected_pairs
        correct_pairs += is_correct
        results.append(
            {
                "prompt_number": prompt_number,
                "entity": entity,
                "predicted_category": answer.choice,
                "confidence": answer.confidence,
                "correct": is_correct,
            }
        )

    precision = correct_pairs / len(predicted_pairs) if predicted_pairs else 0
    recall = correct_pairs / len(expected_pairs) if expected_pairs else 0

    print(
        json.dumps(
            {
                "model": response.model,
                "prompt_count": len(prompts),
                "expected_entity_type_pairs": len(expected_pairs),
                "correct_entity_type_pairs": correct_pairs,
                "entity_type_precision": precision,
                "entity_type_recall": recall,
                "in_process_workflow_ms": round(elapsed_ms, 1),
                "results": results,
            },
            indent=2,
        )
    )

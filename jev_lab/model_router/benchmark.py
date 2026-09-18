from __future__ import annotations

import json
import os
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv

from ..shared.provider import JevProvider
from .router import route_questions, routing_decision

EXAMPLES_PATH = Path(__file__).parent / "data" / "model_router_examples.json"


def main() -> None:
    load_dotenv()
    if not os.getenv("TYPESAFE_API_KEY") or os.getenv("TYPESAFE_API_KEY") == "replace_me":
        raise SystemExit("Set TYPESAFE_API_KEY in .env before running this benchmark.")

    examples = json.loads(EXAMPLES_PATH.read_text())
    tasks = [example["task"] for example in examples]
    providers = [example["provider"] for example in examples]
    start = perf_counter()
    response = JevProvider().evaluate(
        {"tasks": tasks, "provider_constraints": providers},
        route_questions(tasks, providers),
    )
    elapsed_ms = (perf_counter() - start) * 1_000

    results = []
    matches = 0
    for number, example in enumerate(examples, start=1):
        route = routing_decision(response.answers[f"task_{number}"], example["provider"])
        matches += route["model"] == example["expected_model"]
        results.append(
            {
                "task": example["task"],
                "eligible_provider": example["provider"],
                "expected_policy_route": example["expected_model"],
                "selected_model": route["model"],
                "confidence": route["confidence"],
                "matches_policy": route["model"] == example["expected_model"],
            }
        )

    print(json.dumps({
        "model": response.model,
        "example_count": len(examples),
        "policy_matches": matches,
        "policy_agreement": matches / len(examples),
        "in_process_workflow_ms": round(elapsed_ms, 1),
        "results": results,
    }, indent=2))

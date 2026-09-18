"""Resolve one natural-language prompt to entity, metric, and period metadata."""

from __future__ import annotations

import argparse
import json
import os
from time import perf_counter

from dotenv import load_dotenv

from ..shared.provider import JevProvider
from .layer import load_semantic_layer, prepare_question, resolve_answers


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve a financial prompt into semantic metadata.")
    parser.add_argument("question", help="Natural-language finance question")
    args = parser.parse_args()
    load_dotenv()
    if not os.getenv("TYPESAFE_API_KEY") or os.getenv("TYPESAFE_API_KEY") == "replace_me":
        parser.error("Set TYPESAFE_API_KEY in .env before resolving a question.")

    start = perf_counter()
    layer = load_semantic_layer()
    graph = layer["metric_graph"]
    catalog = layer["entities"]
    mentions, period, questions = prepare_question(args.question, graph, catalog)
    api_start = perf_counter()
    response = JevProvider().evaluate(
        {"semantic_layer": layer, "question": args.question},
        questions,
    )
    api_ms = (perf_counter() - api_start) * 1_000
    resolution = resolve_answers(response.answers, mentions, period, graph)
    total_ms = (perf_counter() - start) * 1_000
    print(
        json.dumps(
            {
                "model": response.model,
                "semantic_layer_id": layer["layer_id"],
                "question": args.question,
                "resolution": resolution,
                "timing": {
                    "api_call_ms": round(api_ms, 1),
                    "end_to_end_in_process_ms": round(total_ms, 1),
                },
            },
            indent=2,
        )
    )

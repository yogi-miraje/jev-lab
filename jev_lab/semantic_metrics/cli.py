from __future__ import annotations

import argparse
import json
import os

from dotenv import load_dotenv

from ..shared.provider import JevProvider
from .resolver import load_semantic_graph, metric_question, semantic_metric_decision


def main() -> None:
    parser = argparse.ArgumentParser(description="Map a financial question to one semantic metric ID.")
    parser.add_argument("question", help="Natural-language finance question")
    args = parser.parse_args()

    load_dotenv()
    if not os.getenv("TYPESAFE_API_KEY") or os.getenv("TYPESAFE_API_KEY") == "replace_me":
        parser.error("Set TYPESAFE_API_KEY in .env before resolving a metric.")

    graph = load_semantic_graph()
    response = JevProvider().evaluate(
        {"semantic_knowledge_graph": graph, "question": args.question},
        {"metric": metric_question(args.question, graph)},
    )
    print(
        json.dumps(
            {
                "model": response.model,
                "question": args.question,
                "resolution": semantic_metric_decision(response.answers["metric"], graph),
            },
            indent=2,
        )
    )

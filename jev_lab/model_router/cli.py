from __future__ import annotations

import argparse
import json
import os

from dotenv import load_dotenv

from ..shared.provider import JevProvider
from .router import routing_decision, routing_question


def main() -> None:
    parser = argparse.ArgumentParser(description="Route a task to the most cost-effective eligible model.")
    parser.add_argument("task", help="Plain-English task description, including volume, risk, and latency needs")
    parser.add_argument("--provider", choices=["any", "openai", "anthropic"], default="any")
    args = parser.parse_args()

    load_dotenv()
    if not os.getenv("TYPESAFE_API_KEY") or os.getenv("TYPESAFE_API_KEY") == "replace_me":
        parser.error("Set TYPESAFE_API_KEY in .env before routing.")

    response = JevProvider().evaluate(
        {"task": args.task, "provider_constraint": args.provider},
        {"recommended_model": routing_question(args.provider, args.task)},
    )
    print(json.dumps({"model": response.model, "route": routing_decision(response.answers["recommended_model"], args.provider)}, indent=2))

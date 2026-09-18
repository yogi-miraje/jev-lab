from __future__ import annotations

import argparse
import json
import os

from dotenv import load_dotenv

from ..shared.provider import JevProvider
from .policy import decide
from .questions import support_questions


def main() -> None:
    parser = argparse.ArgumentParser(description="Route a support message with TypeSafe Jev.")
    parser.add_argument("message", nargs="+", help="Support message to evaluate")
    args = parser.parse_args()

    load_dotenv()
    if not os.getenv("TYPESAFE_API_KEY") or os.getenv("TYPESAFE_API_KEY") == "replace_me":
        parser.error("Set TYPESAFE_API_KEY in .env (copy .env.example first).")

    response = JevProvider().evaluate(" ".join(args.message), support_questions())
    payload = {
        "model": response.model,
        "answers": {
            "refund_requested": response.answers["refund_requested"].noul,
            "route": response.answers["route"].choice,
            "route_confidence": response.answers["route"].confidence,
            "urgency": response.answers["urgency"].score,
        },
        "decision": decide(response.answers),
    }
    print(json.dumps(payload, indent=2))

from __future__ import annotations

import argparse
import json
import os

from dotenv import load_dotenv

from ..shared.provider import JevProvider
from .classifier import entity_questions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Classify known financial-entity candidates in a piece of text using TypeSafe Jev."
    )
    parser.add_argument("text", help="Text that gives context to the candidate entities")
    parser.add_argument(
        "--entities",
        required=True,
        help="Comma-separated candidate names, e.g. 'Apple,S&P 500,SPY'",
    )
    args = parser.parse_args()

    load_dotenv()
    if not os.getenv("TYPESAFE_API_KEY") or os.getenv("TYPESAFE_API_KEY") == "replace_me":
        parser.error("Set TYPESAFE_API_KEY in .env (copy .env.example first).")

    entities = [entity.strip() for entity in args.entities.split(",") if entity.strip()]
    if not entities:
        parser.error("Provide at least one candidate entity using --entities.")

    questions, names_by_id = entity_questions(entities)
    state = {"text": args.text, "candidate_entities": entities}
    response = JevProvider().evaluate(state, questions)
    classifications = [
        {
            "entity": names_by_id[question_id],
            "category": answer.choice,
            "confidence": answer.confidence,
            "probabilities": answer.probabilities,
        }
        for question_id, answer in response.answers.items()
    ]
    print(json.dumps({"model": response.model, "classifications": classifications}, indent=2))

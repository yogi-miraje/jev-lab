"""Repeat ten fixed semantic-layer questions in batch or individually."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from time import perf_counter
from typing import Any

from dotenv import load_dotenv

from ..shared.provider import JevProvider
from .date_benchmark import SOURCES, score
from .date_classification import date_question, expected_date_label
from .layer import load_semantic_layer, prepare_question, resolve_answers
from .layer_benchmark import load_dataset

# One question per metric, fixed before the repeatability run. Indices are 1-based.
SAMPLE_REFERENCES = (
    ("newer_50", 4),
    ("newer_50", 10),
    ("fresh_50", 13),
    ("fresh_50", 20),
    ("newer_50", 23),
    ("original_100", 30),
    ("fresh_50", 32),
    ("newer_50", 40),
    ("fresh_50", 41),
    ("newer_50", 46),
)


def sample_rows() -> list[tuple[str, dict[str, Any]]]:
    by_source = {name: load_dataset(path) for name, path in SOURCES}
    rows = [(source, by_source[source][number - 1]) for source, number in SAMPLE_REFERENCES]
    if len(rows) != 10 or len({row["metric"] for _, row in rows}) != 10:
        raise ValueError("Repeatability sample must cover ten different metrics")
    return rows


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def answer_record(answer: Any) -> dict[str, Any]:
    return {
        "choice": answer.choice,
        "confidence": answer.confidence,
        "probabilities": answer.probabilities,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Repeat ten fixed questions across ten rounds.")
    parser.add_argument("--runs", type=int, default=10, help="Number of identical calls (default: 10)")
    parser.add_argument(
        "--mode", choices=("individual", "batch"), default="individual",
        help="Call each prompt separately, or repeat one ten-question batch",
    )
    args = parser.parse_args()
    if args.runs < 2:
        parser.error("--runs must be at least 2")
    load_dotenv()
    if not os.getenv("TYPESAFE_API_KEY") or os.getenv("TYPESAFE_API_KEY") == "replace_me":
        parser.error("Set TYPESAFE_API_KEY in .env before running this benchmark.")

    layer = load_semantic_layer()
    graph = layer["metric_graph"]
    catalog = layer["entities"]
    rows = sample_rows()
    prepared = []
    questions: dict[str, object] = {}
    for index, (_, row) in enumerate(rows, start=1):
        mentions, rule_period, local_questions = prepare_question(row["question"], graph, catalog)
        prepared.append((mentions, rule_period))
        for name, question in local_questions.items():
            questions[f"q{index}_{name}"] = question
        questions[f"q{index}_date"] = date_question(row["question"])
    batch_state = {"semantic_layer": layer, "questions": [row["question"] for _, row in rows]}

    choices_by_question = [[] for _ in rows]
    exact_by_question = [[] for _ in rows]
    correct_by_question = [[] for _ in rows]
    confidence_by_question: list[dict[str, list[float]]] = [
        {"metric": [], "date": [], "target": []} for _ in rows
    ]
    all_answers_hashes = []
    full_output_hashes = []
    model_names = []
    per_run_correct = []
    call_ms = []

    for _ in range(args.runs):
        call_start = perf_counter()
        if args.mode == "batch":
            response = JevProvider().evaluate(batch_state, questions)
            api_answers = response.answers
            model_names.append(response.model)
        else:
            api_answers = {}
            for index, (_, row) in enumerate(rows, start=1):
                local_questions = {
                    name: question for name, question in questions.items()
                    if name.startswith(f"q{index}_")
                }
                response = JevProvider().evaluate(
                    {"semantic_layer": layer, "question": row["question"]},
                    local_questions,
                )
                api_answers.update(response.answers)
                model_names.append(response.model)
        call_ms.append(round((perf_counter() - call_start) * 1000, 1))
        all_answers_hashes.append(digest({
            name: answer_record(answer) for name, answer in api_answers.items()
        }))
        full_outputs = []
        correct_count = 0
        for index, ((_, row), (mentions, rule_period)) in enumerate(zip(rows, prepared), start=1):
            metric_answer = api_answers[f"q{index}_metric"]
            date_answer = api_answers[f"q{index}_date"]
            answers = {"metric": metric_answer}
            model_answers = {
                "metric": answer_record(metric_answer),
                "date": answer_record(date_answer),
            }
            confidence_by_question[index - 1]["metric"].append(metric_answer.confidence)
            confidence_by_question[index - 1]["date"].append(date_answer.confidence)
            if len(mentions) > 1:
                target_answer = api_answers[f"q{index}_target_entity"]
                answers["target_entity"] = target_answer
                model_answers["target"] = answer_record(target_answer)
                confidence_by_question[index - 1]["target"].append(target_answer.confidence)
            resolved = resolve_answers(answers, mentions, rule_period, graph)
            choices = {
                "entities": [item["entity_id"] for item in resolved["entities"]],
                "target": resolved["target_entity_id"],
                "metric": resolved["metric_id"],
                "date": date_answer.choice,
            }
            choices_by_question[index - 1].append(canonical(choices))
            exact_by_question[index - 1].append(digest(model_answers))
            full_outputs.append({"resolved": resolved, "date": model_answers["date"]})
            correct = score(row, resolved, date_answer.choice)["joint"]
            correct_by_question[index - 1].append(correct)
            correct_count += int(correct)
        full_output_hashes.append(digest(full_outputs))
        per_run_correct.append(correct_count)

    question_results = []
    for index, ((source, row), choices, exact, correct, confidences) in enumerate(
        zip(rows, choices_by_question, exact_by_question, correct_by_question, confidence_by_question),
        start=1,
    ):
        modal_count = max(Counter(choices).values())
        question_results.append({
            "number": index,
            "source": source,
            "question": row["question"],
            "expected": {
                "entities": row["entities"],
                "target": row["target"],
                "metric": row["metric"],
                "date": expected_date_label(row["period"]),
            },
            "first_prediction": json.loads(choices[0]),
            "same_choice_as_mode": modal_count,
            "distinct_choice_outputs": len(set(choices)),
            "distinct_exact_model_answers": len(set(exact)),
            "correct_runs": sum(correct),
            "confidence_ranges": {
                name: [round(min(values), 6), round(max(values), 6)]
                for name, values in confidences.items() if values
            },
        })

    print(json.dumps({
        "model_names": sorted(set(model_names)),
        "mode": args.mode,
        "question_count": len(rows),
        "run_count": args.runs,
        "api_call_count": args.runs * (len(rows) if args.mode == "individual" else 1),
        "total_question_evaluations": len(rows) * args.runs,
        "questions_with_identical_choices_all_runs": sum(
            item["distinct_choice_outputs"] == 1 for item in question_results
        ),
        "modal_choice_agreement": round(
            sum(item["same_choice_as_mode"] for item in question_results)
            / (len(rows) * args.runs), 4
        ),
        "distinct_exact_api_answer_batches": len(set(all_answers_hashes)),
        "distinct_exact_final_output_batches": len(set(full_output_hashes)),
        "correct_complete_answers_by_run": per_run_correct,
        "api_call_ms_by_run": call_ms,
        "questions": question_results,
    }, indent=2))


if __name__ == "__main__":
    main()

"""Jev-based model routing with a transparent, locally stored policy profile."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typesafe_sdk import Choice

PROFILES_PATH = Path(__file__).parent / "data" / "model_profiles.json"


def load_profiles() -> dict[str, Any]:
    return json.loads(PROFILES_PATH.read_text())


def eligible_models(provider: str = "any") -> dict[str, Any]:
    models = load_profiles()["models"]
    if provider == "any":
        return models
    return {name: profile for name, profile in models.items() if profile["provider"] == provider}


def routing_criteria(provider: str = "any") -> dict[str, str]:
    models = eligible_models(provider)
    if not models:
        raise ValueError("provider must be one of: any, openai, anthropic")
    return {
        name: (
            f"Route when: {profile['route_when']} "
            f"Avoid when: {profile['avoid_when']} "
            f"Artificial Analysis snapshot: {profile['aa_snapshot']}"
        )
        for name, profile in models.items()
    }


def routing_question(provider: str = "any", task: str | None = None) -> Choice:
    task_context = f"\n\nTask to route: {task}" if task else ""
    return Choice(
        instructions=(
            "Choose the single eligible model that should solve this task at the lowest expected cost "
            "while meeting its explicit quality, latency, volume, and risk requirements. "
            "Honor a named provider requirement. Do not choose a higher-cost model merely because it is stronger."
            f"{task_context}"
        ),
        criteria=routing_criteria(provider),
    )


def route_questions(tasks: list[str], providers: list[str] | None = None) -> dict[str, object]:
    providers = providers or ["any"] * len(tasks)
    if len(tasks) != len(providers):
        raise ValueError("tasks and providers must have equal lengths")
    return {
        f"task_{number}": routing_question(provider, task)
        for number, (task, provider) in enumerate(zip(tasks, providers), start=1)
    }


def routing_decision(answer: Any, provider: str = "any") -> dict[str, Any]:
    profiles = eligible_models(provider)
    selected = profiles[answer.choice]
    return {
        "model": answer.choice,
        "provider": selected["provider"],
        "confidence": answer.confidence,
        "probabilities": answer.probabilities,
        "policy_basis": selected["route_when"],
        "needs_human_review": answer.confidence < 0.75,
    }

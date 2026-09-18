"""The deliberately narrow boundary between this app and TypeSafe's SDK."""

from __future__ import annotations

from typing import Any

from typesafe_sdk import TypeSafeClient


class JevProvider:
    def __init__(self) -> None:
        # TypeSafeClient reads TYPESAFE_API_KEY from the environment.
        self.client = TypeSafeClient()

    def evaluate(self, state: Any, questions: dict[str, object]) -> Any:
        return self.client.system_one(state=state, questions=questions)

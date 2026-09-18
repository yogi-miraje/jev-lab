"""Atomic Jev questions for a simple support-ticket workflow."""

from typesafe_sdk import Choice, Noul, Score


def support_questions() -> dict[str, object]:
    return {
        "refund_requested": Noul(
            instructions="Is the customer explicitly asking for a refund?",
            criteria={
                "true": "The customer directly asks for money back or cancellation with a refund.",
                "false": "The customer does not explicitly ask for a refund.",
            },
        ),
        "route": Choice(
            instructions="Which team should handle this support message?",
            criteria={
                "billing": "Payment, subscription, duplicate-charge, or refund issues",
                "technical": "Bugs, login failures, crashes, or integrations",
                "general": "Everything else",
            },
        ),
        "urgency": Score(
            instructions="How urgent is this support message?",
            criteria=[
                "Routine: no time-sensitive harm",
                "Same-day: a problem blocking normal use or money at risk",
                "Immediate: security, fraud, or an account lockout",
            ],
        ),
    }

"""Application-owned thresholds and actions; no model call belongs here."""

from __future__ import annotations

from typing import Any


def decide(answers: dict[str, Any]) -> dict[str, str]:
    refund = answers["refund_requested"]
    route = answers["route"]
    urgency = answers["urgency"]

    if urgency.score >= 2:
        return {"action": "escalate-now", "team": route.choice, "reason": "high urgency"}
    if refund.noul >= 0.8 and route.confidence >= 0.8:
        return {"action": "offer-refund-review", "team": "billing", "reason": "high-confidence refund request"}
    return {"action": "queue", "team": route.choice, "reason": "normal triage"}

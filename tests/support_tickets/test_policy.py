from types import SimpleNamespace

from jev_lab.support_tickets.policy import decide


def answers(*, refund: float, route: str, confidence: float, urgency: float):
    return {
        "refund_requested": SimpleNamespace(noul=refund),
        "route": SimpleNamespace(choice=route, confidence=confidence),
        "urgency": SimpleNamespace(score=urgency),
    }


def test_refund_with_confident_billing_route_goes_to_review():
    result = decide(answers(refund=0.94, route="billing", confidence=0.9, urgency=1.0))
    assert result["action"] == "offer-refund-review"
    assert result["team"] == "billing"


def test_high_urgency_overrides_normal_queueing():
    result = decide(answers(refund=0.0, route="technical", confidence=0.8, urgency=2.1))
    assert result["action"] == "escalate-now"
    assert result["team"] == "technical"

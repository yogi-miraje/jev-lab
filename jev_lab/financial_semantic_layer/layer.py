"""Resolve entity, metric, and reporting period from a finance question."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from typesafe_sdk import Choice

from .resolver import load_semantic_graph, metric_question, semantic_metric_decision

ENTITY_CATALOG_PATH = Path(__file__).parent / "data" / "entity_catalog.json"

# These aliases extend the canonical names in the semantic layer. Keep ambiguous
# short words out of this table: a false match is worse than an abstention.
ENTITY_ALIASES = {
    "Apple": ["AAPL", "Apple Inc."],
    "Microsoft": ["MSFT", "Microsoft Corp."],
    "NVIDIA": ["NVDA", "Nvidia"],
    "Alphabet": ["GOOGL", "Google"],
    "Meta Platforms": ["META", "Meta"],
    "Tesla": ["TSLA"],
    "Amazon": ["AMZN"],
    "JPMorgan Chase": ["JPM", "JPMorgan"],
    "Berkshire Hathaway": ["BRK.B", "Berkshire"],
    "Taiwan Semiconductor Manufacturing Company": ["TSMC"],
    "Novo Nordisk": ["NVO"],
    "S&P 500": ["SPX"],
    "Nasdaq Composite": ["COMP"],
    "Vanguard Total Stock Market ETF": ["VTI"],
    "SPDR S&P 500 ETF Trust": ["SPY"],
    "ARK Innovation ETF": ["ARKK"],
    "Invesco QQQ Trust": ["QQQ"],
    "gold": ["gold bullion"],
}


@dataclass(frozen=True)
class EntityMention:
    entity_id: str
    name: str
    category: str
    matched_text: str
    start: int
    end: int

    def as_dict(self) -> dict[str, str]:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "category": self.category,
            "matched_text": self.matched_text,
        }


def entity_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return f"entity.{slug}"


def load_entity_catalog() -> list[dict[str, Any]]:
    rows = json.loads(ENTITY_CATALOG_PATH.read_text())
    result = [
        {
            "id": entity_id(row["entity"]),
            "name": row["entity"],
            "category": row["expected_category"],
            "aliases": ENTITY_ALIASES.get(row["entity"], []),
        }
        for row in rows
    ]
    if len({row["id"] for row in result}) != len(result):
        raise ValueError("Entity catalog IDs must be unique")
    return result


def load_semantic_layer() -> dict[str, Any]:
    """The fixed metadata shared by every question in this experiment."""
    return {
        "layer_id": "financial-semantic-layer-v1",
        "metric_graph": load_semantic_graph(),
        "entities": load_entity_catalog(),
        "relations": [
            {
                "subject_category": "company",
                "predicate": "has_financial_fundamental",
                "object_metric_group": "financial_fundamentals",
            }
        ],
        "period_schema": {
            "explicit": ["quarter", "year"],
            "relative": [
                "latest_reported_quarter", "previous_reported_quarter",
                "latest_reported_year", "previous_reported_year",
                "current_year", "year_to_date", "trailing_twelve_months",
            ],
            "missing": "unspecified",
            "fiscal_calendar_rule": "Keep relative periods symbolic until an issuer calendar and as-of date are available.",
        },
    }


def match_entities(question: str, catalog: list[dict[str, Any]]) -> list[EntityMention]:
    """Match known names/aliases, preferring the longest non-overlapping span."""
    candidates: list[EntityMention] = []
    for entity in catalog:
        for phrase in [entity["name"], *entity["aliases"]]:
            pattern = rf"(?<!\w){re.escape(phrase)}(?!\w)"
            for match in re.finditer(pattern, question, flags=re.IGNORECASE):
                candidates.append(
                    EntityMention(
                        entity["id"], entity["name"], entity["category"],
                        match.group(), match.start(), match.end(),
                    )
                )
    chosen: list[EntityMention] = []
    for item in sorted(candidates, key=lambda m: (-(m.end - m.start), m.start)):
        if not any(item.start < other.end and other.start < item.end for other in chosen):
            chosen.append(item)
    by_id: dict[str, EntityMention] = {}
    for item in sorted(chosen, key=lambda m: m.start):
        by_id.setdefault(item.entity_id, item)
    return list(by_id.values())


def target_question(question: str, mentions: list[EntityMention]) -> Choice:
    return Choice(
        instructions=(
            "Which mentioned entity is the subject whose financial fundamental is being requested? "
            "Other named entities may be comparison or economic context. Choose one subject. "
            f"Question: {question}"
        ),
        criteria={
            mention.entity_id: (
                f"{mention.name}, a {mention.category}; choose only if the requested metric "
                "belongs to this entity."
            )
            for mention in mentions
        },
    )


def interpret_period(question: str) -> dict[str, Any]:
    """Normalize supported date phrases without guessing issuer fiscal calendars."""
    text = question.lower()
    quarter_patterns = [
        r"\b(?:fiscal\s+)?q([1-4])\s*(?:fy\s*)?(20\d{2})\b",
        r"\b(?:fy\s*)?(20\d{2})\s*q([1-4])\b",
        r"\b([1-4])(?:st|nd|rd|th)\s+quarter\s+(?:of\s+)?(?:fiscal\s+)?(20\d{2})\b",
    ]
    for index, pattern in enumerate(quarter_patterns):
        match = re.search(pattern, text)
        if match:
            if index == 1:
                year, quarter = int(match.group(1)), int(match.group(2))
            else:
                quarter, year = int(match.group(1)), int(match.group(2))
            basis = "fiscal" if re.search(r"(?:\bfy\s*20\d{2}\b|\bfiscal\b)", match.group()) else "unspecified"
            return {"kind": "quarter", "year": year, "quarter": quarter, "basis": basis}

    year_match = re.search(r"\b(?:fy\s*|fiscal\s+(?:year\s+)?)(20\d{2})\b", text)
    if year_match:
        return {"kind": "year", "year": int(year_match.group(1)), "basis": "fiscal"}
    year_match = re.search(r"\b(20\d{2})\b", text)
    if year_match:
        return {"kind": "year", "year": int(year_match.group(1)), "basis": "unspecified"}

    relative_patterns = [
        (r"\b(?:trailing\s+(?:twelve|12)\s+months|ttm|last\s+12\s+months)\b", "trailing_twelve_months"),
        (r"\b(?:latest|most\s+recent)\s+(?:reported\s+)?quarter\b", "latest_reported_quarter"),
        (r"\b(?:last|previous|prior)\s+quarter\b", "previous_reported_quarter"),
        (r"\b(?:latest|most\s+recent)\s+(?:reported\s+)?(?:fiscal\s+)?year\b", "latest_reported_year"),
        (r"\b(?:last|previous|prior)\s+(?:fiscal\s+)?year\b", "previous_reported_year"),
        (r"\b(?:this|current)\s+(?:fiscal\s+)?year\b", "current_year"),
        (r"\b(?:year\s+to\s+date|ytd)\b", "year_to_date"),
    ]
    for pattern, selector in relative_patterns:
        match = re.search(pattern, text)
        if match:
            basis = "fiscal" if "fiscal" in match.group() else "unspecified"
            return {"kind": "relative", "selector": selector, "basis": basis}
    return {"kind": "unspecified"}


def prepare_question(
    question: str, graph: dict[str, Any], catalog: list[dict[str, Any]]
) -> tuple[list[EntityMention], dict[str, Any], dict[str, Choice]]:
    mentions = match_entities(question, catalog)
    questions = {"metric": metric_question(question, graph)}
    if len(mentions) > 1:
        questions["target_entity"] = target_question(question, mentions)
    return mentions, interpret_period(question), questions


def resolve_answers(
    answers: dict[str, Any], mentions: list[EntityMention], period: dict[str, Any],
    graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    graph = graph or load_semantic_graph()
    metric = semantic_metric_decision(answers["metric"], graph)
    target = (
        answers["target_entity"].choice if len(mentions) > 1
        else mentions[0].entity_id if mentions else None
    )
    target_confidence = (
        answers["target_entity"].confidence if len(mentions) > 1
        else 1.0 if mentions else None
    )
    return {
        "entities": [mention.as_dict() for mention in mentions],
        "target_entity_id": target,
        "target_confidence": target_confidence,
        "metric_id": metric["metric_id"],
        "metric_name": metric["canonical_name"],
        "metric_confidence": metric["confidence"],
        "period": period,
        "needs_human_review": (
            metric["needs_human_review"]
            or target is None
            or (target_confidence is not None and target_confidence < 0.75)
        ),
    }

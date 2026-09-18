"""Typed Jev questions for classifying known financial-entity candidates."""

from __future__ import annotations

from typesafe_sdk import Choice


ENTITY_CRITERIA = {
    "company": "An operating company, private company, public company, or its commonly used company name.",
    "fund_or_etf": "A mutual fund, ETF, hedge fund, venture fund, or other pooled investment vehicle.",
    "index": "A market, benchmark, sector, volatility, or economic index, such as the S&P 500.",
    "commodity": "A traded physical commodity or commodity benchmark, such as gold, oil, copper, or wheat.",
    "currency": "A sovereign currency or foreign-exchange unit, such as USD, euro, yen, or pound sterling.",
    "cryptocurrency": "A blockchain-native cryptocurrency, token, stablecoin, or crypto asset.",
    "government_or_central_bank": "A government, regulator, treasury, central bank, or monetary authority.",
    "exchange": "A securities, derivatives, commodities, or cryptocurrency exchange or trading venue.",
    "bond_or_credit_instrument": "A named bond, note, loan, credit default swap, or other debt/credit instrument.",
    "other": "Not one of the listed financial-entity categories, or too ambiguous to classify safely.",
}


def entity_questions(entities: list[str]) -> tuple[dict[str, object], dict[str, str]]:
    """Create one independent Choice question per candidate entity."""
    questions: dict[str, object] = {}
    names_by_id: dict[str, str] = {}
    for number, entity in enumerate(entities, start=1):
        question_id = f"entity_{number}"
        names_by_id[question_id] = entity
        questions[question_id] = Choice(
            instructions=(
                f"Classify the candidate entity '{entity}' using its meaning in the supplied text. "
                "Choose exactly one category. Prefer other when the text does not disambiguate it."
            ),
            criteria=ENTITY_CRITERIA,
        )
    return questions, names_by_id

"""Coarse reporting-period labels that do not resolve years or fiscal calendars."""

from __future__ import annotations

from typing import Any

from typesafe_sdk import Choice

DATE_CRITERIA = {
    "q1": "The requested reporting period is explicitly the first quarter or Q1.",
    "q2": "The requested reporting period is explicitly the second quarter or Q2.",
    "q3": "The requested reporting period is explicitly the third quarter or Q3.",
    "q4": "The requested reporting period is explicitly the fourth quarter or Q4.",
    "quarter": (
        "A quarter is requested, but no quarter number is stated; for example "
        "latest, last, previous, or most recent quarter."
    ),
    "year": (
        "A whole year is requested, whether an explicit year number or a relative "
        "year such as latest, last, previous, or current year. No quarter is requested."
    ),
    "ttm": "A rolling or trailing twelve-month period is requested.",
    "ytd": "A year-to-date period is requested.",
    "none": "No reporting period is requested; ignore year-like numbers in entity names.",
}


def date_question(question: str) -> Choice:
    return Choice(
        instructions=(
            "Classify only the reporting period requested by the finance question. "
            "Ignore the absolute year number and fiscal versus calendar basis. "
            "When a comparison mentions a reference period, choose the period whose "
            "metric is requested. Do not treat numbers in entity names as dates. "
            "Return one of the allowed date labels. "
            f"Question: {question}"
        ),
        criteria=DATE_CRITERIA,
    )


def expected_date_label(period: dict[str, Any]) -> str:
    """Project existing hand-labeled periods onto a coarse, year-free score."""
    kind = period["kind"]
    if kind == "quarter":
        return f"q{period['quarter']}"
    if kind == "year":
        return "year"
    if kind == "unspecified":
        return "none"
    if kind == "relative":
        selector = period["selector"]
        if selector in {"latest_reported_quarter", "previous_reported_quarter"}:
            return "quarter"
        if selector in {"latest_reported_year", "previous_reported_year", "current_year"}:
            return "year"
        if selector == "trailing_twelve_months":
            return "ttm"
        if selector == "year_to_date":
            return "ytd"
    raise ValueError(f"Unsupported period for coarse date scoring: {period}")

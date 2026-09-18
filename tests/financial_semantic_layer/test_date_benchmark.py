from collections import Counter

from jev_lab.financial_semantic_layer.date_benchmark import benchmark_rows, score
from jev_lab.financial_semantic_layer.date_classification import DATE_CRITERIA, expected_date_label
from jev_lab.financial_semantic_layer.repeatability_benchmark import sample_rows


def test_100_question_dataset_has_all_coarse_date_labels():
    rows = benchmark_rows()
    labels = {expected_date_label(row["period"]) for row in rows}
    assert len(rows) == 100
    assert labels == set(DATE_CRITERIA)
    assert set(Counter(row["metric"] for row in rows).values()) == {10}


def test_absolute_year_and_fiscal_basis_are_ignored_but_quarter_number_is_not():
    assert expected_date_label(
        {"kind": "quarter", "quarter": 1, "year": 2025, "basis": "fiscal"}
    ) == "q1"
    assert expected_date_label(
        {"kind": "year", "year": 2024, "basis": "unspecified"}
    ) == "year"
    assert expected_date_label(
        {"kind": "relative", "selector": "latest_reported_quarter", "basis": "unspecified"}
    ) == "quarter"


def test_whole_question_gets_zero_if_date_label_is_wrong():
    row = {
        "entities": ["entity.apple"],
        "target": "entity.apple",
        "metric": "fundamental.revenue",
        "period": {"kind": "quarter", "quarter": 1, "year": 2025, "basis": "unspecified"},
    }
    resolved = {
        "entities": [{"entity_id": "entity.apple"}],
        "target_entity_id": "entity.apple",
        "metric_id": "fundamental.revenue",
        "period": {"kind": "year", "year": 2025, "basis": "unspecified"},
    }
    checks = score(row, resolved, "year")
    assert not checks["date"]
    assert not checks["joint"]
    assert checks["entities"] and checks["target"] and checks["metric"]


def test_repeatability_sample_covers_all_metrics_and_target_selection():
    rows = sample_rows()
    assert len(rows) == 10
    assert len({row["metric"] for row in rows}) == 10
    assert sum(len(row["entities"]) > 1 for row in rows) >= 3

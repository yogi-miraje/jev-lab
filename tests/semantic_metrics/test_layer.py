from collections import Counter
from pathlib import Path

from jev_lab.semantic_metrics.layer import (
    interpret_period,
    load_entity_catalog,
    load_semantic_layer,
    match_entities,
)
from jev_lab.semantic_metrics.layer_benchmark import load_dataset, validate_dataset
from jev_lab.semantic_metrics.resolver import load_semantic_graph

HOLDOUT_PATH = (
    Path(__file__).parents[2]
    / "jev_lab/semantic_metrics/data/semantic_layer_holdout_50.jsonl"
)


def test_hundred_question_dataset_covers_metrics_entities_and_dates():
    layer = load_semantic_layer()
    catalog = layer["entities"]
    graph = layer["metric_graph"]
    rows = load_dataset()
    validate_dataset(rows, catalog, graph)
    assert layer["relations"][0]["subject_category"] == "company"
    assert len(catalog) == 50
    assert len(rows) == 100
    assert set(Counter(row["metric"] for row in rows).values()) == {10}
    assert {row["period"]["kind"] for row in rows} == {
        "quarter", "year", "relative", "unspecified"
    }
    assert {len(row["entities"]) for row in rows} >= {0, 1, 2, 3}
    assert sum(len(row["entities"]) > 1 and row["target"] != row["entities"][0] for row in rows) >= 10


def test_catalog_matching_and_period_normalization_match_labels():
    catalog = load_entity_catalog()
    for row in load_dataset():
        actual = [mention.entity_id for mention in match_entities(row["question"], catalog)]
        assert actual == row["entities"], row["question"]
        assert interpret_period(row["question"]) == row["period"], row["question"]


def test_longer_fund_name_does_not_create_false_index_mention():
    mentions = match_entities("How did SPDR S&P 500 ETF Trust perform?", load_entity_catalog())
    assert [mention.entity_id for mention in mentions] == ["entity.spdr_s_p_500_etf_trust"]


def test_holdout_is_distinct_and_has_five_questions_per_metric():
    layer = load_semantic_layer()
    rows = load_dataset(HOLDOUT_PATH)
    validate_dataset(rows, layer["entities"], layer["metric_graph"])
    original_questions = {row["question"] for row in load_dataset()}
    assert len(rows) == 50
    assert set(Counter(row["metric"] for row in rows).values()) == {5}
    assert not original_questions.intersection(row["question"] for row in rows)

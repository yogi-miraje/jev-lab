from jev_lab.financial_entities.benchmark import DATASET_PATH, PROMPTS_PATH, extract_catalog_mentions
import json


def test_benchmark_has_fifty_unambiguous_rows():
    rows = json.loads(DATASET_PATH.read_text())
    assert len(rows) == 50
    assert {row["expected_category"] for row in rows} == {
        "company", "fund_or_etf", "index", "commodity"
    }


def test_prompt_set_has_one_to_three_entities_and_exact_catalog_matches():
    catalog = json.loads(DATASET_PATH.read_text())
    prompts = json.loads(PROMPTS_PATH.read_text())
    assert len(prompts) == 20
    for row in prompts:
        expected = [item["entity"] for item in row["entities"]]
        assert 1 <= len(expected) <= 3
        assert set(extract_catalog_mentions(row["prompt"], catalog)) == set(expected)

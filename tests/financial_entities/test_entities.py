from jev_lab.financial_entities.classifier import ENTITY_CRITERIA, entity_questions


def test_creates_one_choice_question_for_each_candidate():
    questions, names = entity_questions(["Apple", "S&P 500"])

    assert names == {"entity_1": "Apple", "entity_2": "S&P 500"}
    assert set(questions) == {"entity_1", "entity_2"}
    assert set(ENTITY_CRITERIA) >= {"company", "fund_or_etf", "index", "other"}

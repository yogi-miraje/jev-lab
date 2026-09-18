from jev_lab.financial_semantic_layer.resolver import (
    load_semantic_graph,
    metric_criteria,
    metric_nodes,
    metric_question,
)


def test_semantic_graph_metric_ids_are_unique_and_stable():
    nodes = metric_nodes(load_semantic_graph())
    metric_ids = [node["id"] for node in nodes]
    assert len(metric_ids) == len(set(metric_ids))
    assert "fundamental.revenue" in metric_ids
    assert "fundamental.diluted_eps" in metric_ids


def test_choice_options_are_exactly_the_graph_metric_ids():
    graph = load_semantic_graph()
    criteria = metric_criteria(graph)
    assert set(criteria) == {node["id"] for node in metric_nodes(graph)}
    assert metric_question("What were Apple's sales?", graph).criteria == criteria

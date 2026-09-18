"""Map financial questions to stable metric IDs from a semantic graph."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typesafe_sdk import Choice

SEMANTIC_GRAPH_PATH = Path(__file__).parent / "data" / "financial_semantic_graph.json"


def load_semantic_graph() -> dict[str, Any]:
    return json.loads(SEMANTIC_GRAPH_PATH.read_text())


def metric_nodes(graph: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    graph = graph or load_semantic_graph()
    return [node for node in graph["nodes"] if node["kind"] == "metric"]


def metric_criteria(graph: dict[str, Any] | None = None) -> dict[str, str]:
    """Turn semantic metadata into the closed set of valid Jev answers."""
    return {
        node["id"]: (
            f"Canonical metric: {node['label']}. Definition: {node['definition']} "
            f"Common aliases: {', '.join(node['aliases'])}."
        )
        for node in metric_nodes(graph)
    }


def metric_question(question: str, graph: dict[str, Any] | None = None) -> Choice:
    return Choice(
        instructions=(
            "Map the natural-language finance question to exactly one canonical metric ID in the "
            "provided semantic graph. A company name, period, or requested comparison is context, "
            "not a metric. Distinguish currency amounts from percentages. Do not invent a metric ID. "
            f"Question: {question}"
        ),
        criteria=metric_criteria(graph),
    )


def semantic_metric_decision(answer: Any, graph: dict[str, Any] | None = None) -> dict[str, Any]:
    by_id = {node["id"]: node for node in metric_nodes(graph)}
    metric = by_id[answer.choice]
    return {
        "metric_id": metric["id"],
        "canonical_name": metric["label"],
        "definition": metric["definition"],
        "confidence": answer.confidence,
        "probabilities": answer.probabilities,
        "needs_human_review": answer.confidence < 0.75,
    }

# Jev Lab

Two Python experiments using TypeSafe's Jev SDK: a model router and a financial semantic layer. Each has its own data and benchmarks; only the TypeSafe provider is shared.

## Setup

```sh
uv sync
cp .env.example .env
# Put your TYPESAFE_API_KEY in .env
uv run pytest
```

The commands load `.env` with `python-dotenv`. Git ignores `.env`; `.env.example` has no secret.

## Model router

`jev-route` recommends Luna, Terra, Sol, Haiku, Sonnet, or Opus for a task, subject to a provider constraint. This is a fixed-choice routing policy, not proof that the selected model is objectively best.

```sh
uv run jev-route "Classify 200,000 support tickets into eight labels; minimize cost." --provider any
uv run jev-route-benchmark
```

The router's model profiles and source links are in `jev_lab/model_router/data/model_profiles.json`. Its benchmark compares Jev's choices with 12 hand-labeled everyday tasks in `model_router_examples.json`; the score is agreement with that policy, not real-world task quality. Refresh the profiles before making production decisions.

## Financial semantic layer

`jev-semantic-layer` turns one finance question into a known entity, a stable financial metric ID, and reporting-period metadata. It also lists every known entity mentioned, so a comparison can have several mentions but one target. This is metadata resolution; it does not retrieve financial values.

```sh
uv run jev-semantic-layer "What were Apple's sales in Q2 FY2025 versus the S&P 500?"
uv run jev-semantic-layer-benchmark
```

The pipeline first matches names and aliases against the 50-entry `entity_catalog.json`. Jev chooses one of 10 metric IDs from `financial_semantic_graph.json`; when multiple entities are mentioned, it also chooses the target. The app then normalizes supported date phrases with Python rules. Unknown entity names are not extracted, and relative periods such as “latest quarter” remain symbolic until an issuer calendar and as-of date are available. Low-confidence or missing-target results request human review.

### Evaluation data

All financial data lives in `jev_lab/financial_semantic_layer/data/`:

| File | Purpose |
| --- | --- |
| `semantic_layer_questions_100.jsonl` | Original 100 labeled entity–metric–period questions |
| `semantic_layer_holdout_50.jsonl` | Separately written 50-question holdout |
| `semantic_layer_holdout_additional_50.jsonl` | Additional 50 questions |
| `semantic_layer_date_200.json` | Manifest combining those three sets for a 200-question coarse-date experiment |
| `semantic_layer_date_150.json` | Earlier manifest retained for reproducibility |

The main benchmark awards one point only when the complete entity set, target entity, metric ID, and detailed period all match the expected answer. It reports component accuracy, whole-answer accuracy, API time per batch, and total in-process time. To test another set:

```sh
uv run jev-semantic-layer-benchmark --dataset jev_lab/financial_semantic_layer/data/semantic_layer_holdout_50.jsonl --batch-size 25
```

The separate date benchmark asks Jev to choose a **coarse** label (Q1–Q4, unspecified quarter, year, trailing 12 months, year-to-date, or no date). It ignores absolute years and fiscal/calendar basis, and does **not** change the app's rule-based detailed period output:

```sh
uv run jev-semantic-date-benchmark --batch-size 25
uv run jev-semantic-repeatability --runs 10 --mode individual
```

The repeatability command selects ten fixed questions, one per metric, from the 200 and compares repeated choices and exact confidence values. These authored datasets test known catalog names and wording patterns; they do not estimate accuracy on arbitrary production questions.

## Layout

```text
jev_lab/
  model_router/              # routing app, profiles, examples, benchmark
  financial_semantic_layer/  # entity catalog, metric graph, date logic, benchmarks
  shared/                    # TypeSafe provider
tests/                       # tests for the two applications
```

Source: [TypeSafe Quick Start](https://docs.typesafe.ai/introduction/quickstart) · [Jev article](https://flaviocopes.com/jev/)

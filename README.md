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

The only bundled question dataset is `jev_lab/financial_semantic_layer/data/semantic_layer_questions_100.jsonl`: 100 labeled questions, ten per metric. Each row has the question and its expected entity set, target entity, metric ID, and period. The other two files in `data/` are application metadata: `entity_catalog.json` and `financial_semantic_graph.json`.

The main benchmark awards one point only when the complete entity set, target entity, metric ID, and detailed period all match the expected answer. It reports component accuracy, whole-answer accuracy, API time per batch, and total in-process time:

```sh
uv run jev-semantic-layer-benchmark --batch-size 25
```

The separate date benchmark asks Jev to choose a **coarse** label (Q1–Q4, unspecified quarter, year, trailing 12 months, year-to-date, or no date). It ignores absolute years and fiscal/calendar basis, and does **not** change the app's rule-based detailed period output:

```sh
uv run jev-semantic-date-benchmark --batch-size 25
uv run jev-semantic-repeatability --runs 10 --mode individual
uv run jev-semantic-repeatability --runs 10 --mode batch
```

The date and repeatability commands use the same 100-question dataset. The repeatability command selects ten fixed questions, one per metric, and compares repeated choices and exact confidence values. This authored dataset tests known catalog names and wording patterns; it does not estimate accuracy on arbitrary production questions.

### Recorded evaluation (2026-09-18)

The results below used Jev `jev-1.13.0` and the 100-question dataset at SHA-256 `bab581f2a46233ad496d2338a283bee5ea89f3780e82955ccb457a10042b36a6`.

| Evaluation | Exact complete answers | API-call time | Total in-process time |
| --- | ---: | ---: | ---: |
| Main semantic-layer pipeline, 4 batches of 25 | 100/100 | 1,456.2 ms across 4 calls | 1,506.1 ms |
| Separate coarse Jev date experiment, 4 batches of 25 | 100/100 | 1,386.9 ms across 4 calls | 1,432.0 ms |

In the main pipeline, the entity set, target, metric, and **rule-parsed detailed period** each matched 100/100. It sent 120 Jev decision questions: 100 metric choices and 20 target-entity choices. In the separate date experiment, Jev's **coarse date label** matched 100/100; that label is not used by the main CLI. API-call time includes the client request, network, and service response, not just model compute. The main pipeline's 1,506.1 ms is for all 100 questions together; dividing by 100 gives throughput per question, **not** single-question latency.

For repeatability, ten fixed questions were each evaluated ten times:

| Request shape | Stable discrete choices | Exact numeric API answers | Execution time |
| --- | ---: | --- | ---: |
| Individual: 100 separate API calls | 10/10 questions unchanged across all 10 runs | 9 distinct full answer sets across 10 runs; confidence/probabilities varied on 4 questions | 21,944.2 ms API time total; 219.4 ms mean per call |
| Batch: 10 API calls, each with 10 questions | 10/10 questions unchanged across all 10 runs | 5 distinct full answer sets across 10 runs; confidence/probabilities varied on 2 questions | 4,356.0 ms API time total; 435.6 ms mean per 10-question batch |

Every sampled question was completely correct in all ten runs in both request shapes. This is **100% choice consistency on a 10-question sample**, not proof of deterministic numeric output or 100% accuracy on unseen questions. The 100-question set was authored around the known catalog and metrics, and there is no independent holdout in this simplified repository.

## Layout

```text
jev_lab/
  model_router/              # routing app, profiles, examples, benchmark
  financial_semantic_layer/  # entity catalog, metric graph, date logic, benchmarks
  shared/                    # TypeSafe provider
tests/                       # tests for the two applications
```

Source: [TypeSafe Quick Start](https://docs.typesafe.ai/introduction/quickstart) · [Jev article](https://flaviocopes.com/jev/)

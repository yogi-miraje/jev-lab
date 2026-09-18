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

### Results at a glance (2026-09-18)

```text
The same 100 hand-written finance questions
├── Main app                 100/100 complete answers  ·  1.51 s total
└── Separate Jev date test   100/100 coarse labels     ·  1.43 s total

10 of those questions, repeated 10 times each
└── Answer choices stayed the same; numeric scores sometimes changed
```

“Complete answer” means the entities mentioned, the target entity, the metric, **and** the detailed period all matched. Jev chose the metric and sometimes the target; Python parsed the detailed period. The separate Jev date test chose only broad labels such as Q2 or “year.” Its predictions are **not** used by the main app.

**Timing:** Each 100-question run used four API calls of 25 questions. The 1.51 s and 1.43 s figures are totals for all 100—not time per question. In the one-at-a-time repeat test, an API call averaged **219 ms**. A ten-question batch averaged **436 ms**. These API timings include network and service time, not just model computation.

**Consistency:** All ten sampled questions kept the same choices across ten runs, both individually and in batches. Their confidence/probability numbers varied for four questions individually and two in batches. This is a result for a **ten-question sample**, not all 100 repeated questions.

**Limit:** The questions were written around the known entity catalog and ten metrics. With no independent holdout, 100/100 on this set does **not** tell us the accuracy on questions from the wild.

Run details: Jev `jev-1.13.0`; dataset SHA-256 `bab581f2a46233ad496d2338a283bee5ea89f3780e82955ccb457a10042b36a6`.

## Layout

```text
jev_lab/
  model_router/              # routing app, profiles, examples, benchmark
  financial_semantic_layer/  # entity catalog, metric graph, date logic, benchmarks
  shared/                    # TypeSafe provider
tests/                       # tests for the two applications
```

Source: [TypeSafe Quick Start](https://docs.typesafe.ai/introduction/quickstart) · [Jev article](https://flaviocopes.com/jev/)

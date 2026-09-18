# Jev Lab

A compact Python experiment using TypeSafe's Jev SDK. Each use case lives in its own package with its own data and tests; only the TypeSafe provider is shared. Jev produces typed, probabilistic decisions while the application owns action thresholds and side effects.

## Setup

```sh
uv sync
cp .env.example .env
# Edit .env and add your real TYPESAFE_API_KEY
uv run jev-lab "I was charged twice and want a refund right away."
uv run pytest
```

The CLI loads `.env` automatically with `python-dotenv`. `.env` is ignored by Git and `.env.example` contains no secret.

## What it sends

The live provider calls `TypeSafeClient().system_one()` with the default `jev-latest` model and three independent questions:

- `Noul`: whether the customer explicitly requests a refund
- `Choice`: whether billing, technical, or general support should own the ticket
- `Score`: a three-level urgency rubric

`jev_lab/policy.py` then makes the action decision in ordinary Python. This is intentional: confidence thresholds stay reviewable and changeable without changing the model prompt.

Source: [TypeSafe Quick Start](https://docs.typesafe.ai/introduction/quickstart) · [article](https://flaviocopes.com/jev/)

## Financial entity classification

Jev classifies *known candidate names*. It does not extract arbitrary new spans from prose, so provide candidates from a watchlist, ticker matcher, database search, or another NER step.

```sh
uv run jev-entities \
  "Apple and the Vanguard Total Stock Market ETF outperformed the S&P 500." \
  --entities "Apple,Vanguard Total Stock Market ETF,S&P 500"
```

The categories are: `company`, `fund_or_etf`, `index`, `commodity`, `currency`, `cryptocurrency`, `government_or_central_bank`, `exchange`, `bond_or_credit_instrument`, and `other`. The output includes each classification and its confidence.

Run the bundled 20-item sanity-check sample with:

```sh
uv run jev-entities-benchmark
```

It reports exact-match accuracy against its intentionally unambiguous labels and the in-process time from question construction through the API response.

## Model router

`jev-route` selects one of Luna, Terra, Sol, Haiku, Sonnet, or Opus for a plain-English task. It treats the choice as a **routing recommendation**, not a benchmark claim: the router's decision policy is based on a dated Artificial Analysis snapshot plus explicit task constraints.

```sh
uv run jev-route \
  "Classify 200,000 support tickets into eight predefined labels; minimize cost." \
  --provider any

uv run jev-route-benchmark
```

The benchmark uses day-to-day examples and reports agreement with the project's declared routing policy, plus time. Profiles and source URLs are in `jev_lab/model_router/data/model_profiles.json`; update them before using the router as a lasting production policy.

## Financial semantic-metric resolution

`jev-semantic-metric` maps a natural-language finance question to one stable metric ID from a shared semantic graph. The same graph is included for every request; only the natural-language question changes. The output is a canonical metric ID, display name, definition, probabilities, and a low-confidence review flag.

```sh
uv run jev-semantic-metric "What were Apple's sales in fiscal 2025?"
uv run jev-semantic-metric-benchmark
```

The graph is `jev_lab/semantic_metrics/data/financial_semantic_graph.json`. It contains unique IDs and metadata for revenue, revenue growth, gross profit, gross margin, operating income, net income, diluted EPS, R&D expense, free cash flow, and capital expenditures. The ten-question benchmark measures exact metric-ID accuracy, not whether a financial value was retrieved.

## Combined financial semantic layer

The combined command returns all known entities mentioned, the entity whose fundamental is requested, the metric ID, and normalized period metadata. It reuses the 50-name catalog from `financial_entities` and the metric graph above. Dates like `Q2 FY2025` become structured quarter/year values; `latest quarter` remains a relative selector, and a missing date stays unspecified. A question without an entity returns a null target and requests human review.

```sh
uv run jev-semantic-layer "What were Apple's sales in Q2 FY2025 versus the S&P 500?"
uv run jev-semantic-layer-benchmark
uv run jev-semantic-layer-benchmark --details
uv run jev-semantic-layer-benchmark --dataset jev_lab/semantic_metrics/data/semantic_layer_holdout_50.jsonl --batch-size 25
```

The 100-question dataset is `jev_lab/semantic_metrics/data/semantic_layer_questions_100.jsonl`. It has ten questions per metric, with single, multiple, and missing entities, plus explicit, relative, and missing dates. Some comparison prompts mention context entities before the actual target. The benchmark sends two batches of 50 questions because one 100-question request exceeds TypeSafe's token limit; `--batch-size` can lower the batch size. It reports exact matches for the entity set, target entity, metric ID, period, and whole record, plus per-batch API time and total workflow time. Entity names and aliases are matched against the known catalog; period normalization handles the documented patterns. Results do not imply coverage of unknown entities, arbitrary date wording, or retrieved financial values.

The separate 50-question holdout was labeled before the live Jev run and shares no question text with the original set. It has five fresh questions per metric, including different quarter wording, relative dates, context entities, and ticker variants. Score each question as 1 only when its complete entity set, target, metric ID, and period all match; otherwise score 0. On the 2026-09-18 run, exact-match accuracy was **31/50 (62%)**. Component matches were entities 48/50, target 48/50, metric 50/50, and period 32/50. The metric-balanced, hand-authored set is a stress check, not a random sample of production questions, so 62% is not a population accuracy estimate. The dataset SHA-256 at the time of this run was `00e388f9d58103abf355d6b45fba57ceffc11f917bdf2bbff6fe6baba01eb847`.

### Coarse date experiment across 200 questions

`jev_lab/semantic_metrics/data/semantic_layer_date_200.json` combines the original 100, the earlier fresh 50, and an additional 50 labeled before this rerun. The expanded fresh set has 100 questions (ten per metric). The additional questions avoid calendar years, and the Jev date-choice criteria were not changed after they were written. For this experiment, the date target is one of Q1–Q4, quarter with no stated number, whole year, trailing 12 months, year-to-date, or no date. It ignores absolute year numbers and fiscal/calendar basis. Each complete answer gets 1 only if its entity set, target, metric ID, and coarse date label all match; otherwise 0.

```sh
uv run jev-semantic-date-benchmark --batch-size 25
```

On the 2026-09-18 Jev 1.13.0 run, the model-based coarse date answer was correct on **200/200**, and the complete answer on **196/200 (98%)**. The expanded fresh 100 scored **96/100**; the newly added 50 scored **48/50**. The four full-answer failures were missing catalog aliases TSM, GOOG, Samsung, and Toyota. Entity and target accuracy were 196/200, while metric accuracy was 200/200. For comparison, the original rule-based date parser got 150/200 coarse date labels and 148/200 complete answers. This is a separate evaluation path: `jev-semantic-layer` still returns its original rule-parsed detailed period. These authored questions and fixed answer choices are not a random sample of production traffic, so the result is not a real-world accuracy estimate. The additional 50-question dataset SHA-256 was `bae6551f248a6b6070a265613b3ae65d46e25d387ec41b33477c1a462924110a` at the time of the run. The earlier 150-question manifest is retained for reproducibility.

### Repeatability check

`jev-semantic-repeatability` uses a fixed sample of ten questions, one per metric, including three multi-entity questions. It compares discrete choices separately from exact numeric API answers:

```sh
uv run jev-semantic-repeatability --runs 10 --mode individual
uv run jev-semantic-repeatability --runs 10 --mode batch
```

On the 2026-09-18 Jev 1.13.0 runs, each question kept the same entity, target, metric, and date choices across its ten repeated single-question calls (100/100 choice agreements). The ten-question batch also kept the same choices across ten repeated batch calls. However, the exact confidence/probability answer changed for four of ten questions in the individual test, so the complete numeric API output was not identical across runs. Complete-answer accuracy was 8/10 in every run: the date label for “How fast are Tesla's sales growing compared with a year ago?” was consistently `year` rather than the gold `none`, and “Toyota” was consistently absent from the catalog match. The Tesla date had scored `none` in the earlier 200-question batch, so repeatability under one fixed request shape does not guarantee the same result under different batching or conditions.

## Project layout

```text
jev_lab/
  shared/                 # TypeSafe provider used by all examples
  support_tickets/        # triage questions, policy, CLI
  financial_entities/     # candidate classifier, data, CLI, benchmark
  model_router/           # routing policy, data, CLI, benchmark
  semantic_metrics/       # semantic graph, resolver, CLI, benchmark
tests/                    # mirrors the four use cases
```

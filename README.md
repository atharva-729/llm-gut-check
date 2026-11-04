# Gut-Check Harness

**Should this task run on the fast mode or the thinking mode? Can the model's confidence be trusted to skip human review?**

A reusable audit tool. Plug in any task where the correct answers are known. The harness asks every item twice, once with thinking **off** (the "gut") and once with thinking **on** (the "reasoned" answer), across several models. It then produces a one-page **verdict** per task, for example:

> **Banking query intent, `gpt-5.4-mini`:** use **fast mode**. Thinking adds +0.8 pts accuracy (CI includes 0) at 14× the cost. **Auto-accept at confidence ≥ 85%**: 99.1% precision (lower bound 98.4%), covering **71%** of queries. The other 29% go to human review. Overthinking flips (right → wrong): 2.1% of items.

What it measures for each task × model:
1. **Accuracy:** gut vs reasoned, with confidence intervals.
2. **Cost and latency** per 1,000 items in each mode, from real token usage and provider list prices.
3. **Calibration:** does "85% sure" mean right 85% of the time? (ECE, reliability diagram, overconfidence.)
4. **Flips:** when thinking changed the answer, was it a fix (wrong → right) or **overthinking** (right → wrong)?
5. **Safe auto-accept threshold:** the lowest confidence level where precision stays ≥ the target (99% by default; 95% also reported), using a conservative lower bound, plus **coverage** (the share of work above it).
6. **The recommendation:** the cheapest configuration (model + mode) that meets the target.

Context: a personal research build. Intended use: a "mode and threshold advisor" for any team running many LLM pipelines. Other uses:
- setting the share of human review in ops contracts;
- model risk validation evidence for regulated clients;
- drift monitoring when providers update models.

It grows out of an earlier observation: LLM answers given at ≥ 90% confidence were about 99% right.

What it is **not**: a leaderboard ranking models, a live router, or a training project.

Prior work to cite rather than repeat:
- Kahneman & Klein 2009 on when intuition can be trusted (kind vs wicked environments).
- Hagendorff et al. 2023 (LLMs and the Cognitive Reflection Test).
- Work on overthinking (more test-time compute lowering accuracy).
- Model routers (RouteLLM, NotDiamond, Martian), which pick models generically. This harness instead **audits on the client's own task** and produces a defensible threshold.

---

## How to use this README (for Claude Code)

- Work **one phase at a time**. At each **CHECKPOINT**, stop, show what it asks for, and wait for a go-ahead.
- Don't start later phases early. Don't add dependencies that aren't listed here without asking.
- Keep it simple: Python, JSONL/Parquet, a small CLI, plotly. No agent frameworks, no databases, no web server.
- If a sanity check fails, stop and report.

## Ground rules

**Do**
- Send all model calls through one **OpenAI-compatible LLM gateway** (`LLM_API_TOKEN`, `LLM_API_BASE`), using its provider routes (OpenAI, Anthropic, Gemini, Groq).
- Cache every call (model + mode + prompt hash). Use a **resumable job queue**, so a stopped run continues where it left off.
- **Keep spend low** (keep it modest):
  - a soft budget in `config.yaml` (default **$25 total**);
  - the planner estimates cost **before** every run, and the run refuses to start if the estimate would exceed the remaining budget, unless `--force` is given;
  - a running spend log in `runs/spend.json`.
- Use the **native thinking controls** of each model (see Modes). Don't rely on "think step by step" prompting.
- Put long option lists (Banking77, LEDGAR) in the system prompt so provider prompt caching applies, and log cache hits.
- **Pre-register** the hypotheses, metrics, thresholds and exclusion rules in `PREREG.md` before the full run (Phase 1).
- Use the same prompt template across tasks; only the task block changes.
- Write tests for parsing, grading, metrics, threshold search and the verdict rules.

**Don't**
- Don't tune prompts or rules on items used in the final results. Pilot items are separate and never reused.
- Don't give models tools, web access, or any hint of the answer.
- Don't use a forecasting question that resolved **before** a model's training cutoff.
- Don't hand-label anything. Every task has gold answers.
- Don't present results as a model leaderboard. The unit of analysis is the **task**.

---

## Tasks (the demo's "task packs")

Every task is **choose one answer from a fixed set** (or give a probability for yes/no), so grading is automatic and exact.

| Task | Why it's here | Format | Items (main) | Gold / human reference | Licence |
|---|---|---|---|---|---|
| **Grammar (BLiMP)** | **Kind** showcase: regular patterns, huge "experience" | A or B: which sentence is grammatical | 150, stratified across paradigms, A/B order randomised | Gold, plus BLiMP's reported human agreement per paradigm | CC BY |
| **Forecasting (Manifold)** | **Wicked** showcase: a noisy world | Probability that a resolved yes/no question came true | 150 | Gold resolution, plus the **crowd** probability ~24 h before close | Manifold public API |
| **Banking77** | Business: banking customer queries | Pick 1 of 77 intents | 200, stratified by intent | Gold | CC BY 4.0 |
| **LEDGAR** (from LexGLUE) | Business: legal contract clauses | Pick 1 of 100 clause types | 150, stratified | Gold | Check and record |
| **Toxicity (Jigsaw / Civil Comments)** | Business: content moderation | Toxic, yes or no | 200, about 30% toxic (record the ratio) | Gold (majority annotator label) | CC0 (check the variant used) |

Pilot sets: **20 items per task**, separate and never reused.

**Manifold filtering:**
- binary, resolved YES or NO (drop N/A);
- **resolved after the latest training cutoff among the models used** (look up each model's cutoff; if it's unknown, use its release date, which is conservative);
- ≥ 20 unique traders;
- no questions about AI models;
- no markets with ambiguous resolution notes.

Give the model only the question text and close date.

**Task pack format** (so clients can bring their own later):
```
tasks/<task_id>/
  task.yaml      # name, answer_type: single_choice | binary | probability, options (or file), instructions, target_precision
  items.jsonl    # {id, input, gold, human_ref?: float, meta?: {...}}
  pilot.jsonl
```

---

## Models and modes

The main models are the **cheap tier**, because that's what high-volume work actually runs on. One larger model runs on a subset.

| Role | Model (via gateway) | Gut | Reasoned |
|---|---|---|---|
| Main | `gpt-5.4-mini` | `reasoning_effort` = `none` if supported, else `minimal` | `reasoning_effort` = `medium` |
| Main | `claude-haiku-4-5` | extended thinking **off** | thinking **on**, `budget_tokens` ≈ 2,048 |
| Main | `gemini-3.8-flash` | `thinking_budget` = 0 | dynamic/default thinking |
| Large (subset of 50 items per task) | `claude-sonnet-5` **or** `gpt-5.4` (pick one in Phase 0 by price) | same pattern | same pattern |
| Optional, cheap open-weight | `openai/gpt-oss-120b` (Groq) | `reasoning_effort` = `low` (**no true off**; label it) | `high` |

**Verify every mode in Phase 0:** gut calls must report **zero (or minimal) reasoning tokens** in the usage fields. If a model can't really turn thinking off, label that clearly in every result.

**Output format** for all calls (use structured or JSON output where supported):
```json
{"answer": "<option or YES/NO or probability>", "confidence": <0-100>}
```
For `probability` tasks, `answer` is the probability and `confidence` is ignored. Unparseable output gets one retry; after that, the item is marked `parse_fail` and counted.

### Optional arm: Jev (only if access arrives; never blocks anything)
- Jev returns **native probabilities** per option instead of a stated confidence. It's a "decision model" comparison arm.
- **Limit: 64 options per question.** Grammar, toxicity and forecasting run natively. For Banking77 (77) and LEDGAR (100), use a **2-stage** set-up: an embedding shortlist of the top 32 options (`text-embedding-3-small`), then Jev picks from the shortlist. Report **shortlist recall** (how often the gold answer was in the 32), and label these results as "shortlisted", not directly comparable.
- Implement it as a pluggable `arms/jev.py` adapter behind a config flag. With no key, the harness skips it silently, and the reports say "not run".

---

## Metrics and verdict rules

Per task × model × mode:
- **Accuracy** (for probability tasks: accuracy of the > 50% side, plus the **Brier score**), with a 95% bootstrap CI over items.
- **Cost per 1,000 items** = real tokens (input, cached input, output, reasoning) × provider list prices. **Latency:** median and p90.
- **Calibration:** ECE with 10 bins, a reliability diagram, and **overconfidence** = mean confidence − accuracy.
- **Flips** (same item, gut vs reasoned): right→wrong (**overthinking**), wrong→right (**fix**), wrong→wrong, net gain. Also flip rate by item difficulty, where difficulty exists (BLiMP paradigm human agreement, crowd uncertainty).
- **Auto-accept threshold** at target precision *p* (default 0.99, also 0.95): the lowest confidence *t* where the **Wilson lower bound** of precision among items with confidence ≥ *t* is ≥ *p*, with at least 30 items above *t*. Report *t*, precision, its lower bound and **coverage**. If there's no such *t*, say "no safe threshold".

**Verdict rules** (`verdict.py`; deterministic, tested, written into `PREREG.md`):
- **"Use fast mode"** if the reasoned − gut accuracy CI includes 0 **or** the gain is < 1 point.
- Otherwise, **"Use reasoning"**, with the **cost per extra correct answer** stated.
- **"Overthinking risk"** flag if right→wrong flips are ≥ 3% of items **or** ≥ 30% of all flips.
- **"Confidence usable"** if a safe threshold exists with coverage ≥ 30%; otherwise "send everything to review, or don't use confidence".
- **"Cheapest configuration meeting target":** across all models and modes, the lowest cost per 1,000 items whose accuracy CI lower bound is ≥ the task's target, or whose auto-accept set meets the target precision with the highest coverage. Show both.

---

## Repo layout

```
gut-check-harness/
  README.md  PREREG.md  config.yaml  .env.example
  tasks/<task_id>/{task.yaml, items.jsonl, pilot.jsonl}
  prompts/system.md  prompts/blocks/<answer_type>.md
  src/gch/
    llm.py         # gateway clients per provider, mode controls, usage capture
    models.py      # model registry: prices, cutoffs, mode settings
    queue.py       # resumable jobs
    budget.py      # cost planner + soft budget
    build_tasks.py # builds the 5 demo task packs
    parse.py       # JSON parsing, retries
    grade.py
    metrics.py     # accuracy, Brier, ECE, flips, bootstrap
    threshold.py   # Wilson-bound threshold search
    verdict.py     # rules → verdict cards
    crowd.py       # human/crowd comparisons (BLiMP, Manifold)
    drift.py       # rerun + compare to baseline
    arms/jev.py    # optional
    cli.py
  runs/  reports/  docs/  tests/
```

CLI shape:
- `gch probe` (check models and modes)
- `gch build-tasks`
- `gch plan`
- `gch pilot`
- `gch run [--task X] [--force]`
- `gch status`
- `gch analyse`
- `gch verdict --task X`
- `gch new-task --csv file.csv --text-col ... --label-col ...`
- `gch rerun --task X` (drift)
- `gch site`

---

## Phase 0: Setup and model probe

1. Scaffold the repo. Build a gateway client per provider (OpenAI, Anthropic, Gemini, Groq) that captures **usage, including reasoning and cached tokens, and latency** for every call.
2. **`gch probe`:** for each model in the table, run 3 tiny calls in **each mode**. Record:
   - whether the mode setting was accepted;
   - reasoning tokens used (gut must be about 0);
   - JSON-output support;
   - latency.

   Flag any model whose gut mode still reasons.
3. **Model registry** (`models.py` / `config.yaml`): exact model IDs, per-token prices (provider list prices; record the source), and training cutoffs with sources.
4. Pick the large model (Sonnet 5 or GPT-5.4) by price and mode support.
5. **Budget planner:** given task sizes, models, modes and estimated tokens, print the expected cost per task × model × mode and the total. Default soft budget: $25.

### CHECKPOINT 0
Show:
- The probe table (model × mode: accepted?, reasoning tokens, JSON support, latency).
- The model registry.
- The planner's estimate for the full plan.
- Which large model was picked and why.

---

## Phase 1: Build the task packs and pre-register

1. Build all 5 task packs (main + pilot) as specified. Record the source, licence and sampling seed for each in `tasks/<id>/SOURCE.md`.
2. Manifold: apply the cutoff filter using the registry's **latest** cutoff, and attach the crowd probability ~24 h before close.
3. BLiMP: attach the per-paradigm human agreement.
4. Write `PREREG.md`:
   - **H1 (calibration):** gut overconfidence is higher on the wicked task (forecasting) than on the kind task (grammar).
   - **H2 (reasoning value):** on simple business classification (toxicity, Banking77), reasoning gives little or no accuracy gain relative to its cost. On forecasting, reasoning changes answers more but doesn't improve Brier much.
   - **H3 (crowd):** on forecasting, gut probabilities correlate more with the crowd than reasoned probabilities do, including on crowd-confident-wrong questions.
   - **Metrics, verdict rules and threshold method** exactly as above.
   - **Exclusions:** parse failures after retry, counted and reported; gut-mode reasoning leaks, flagged and analysed both ways.

   Commit it before Phase 3.

### CHECKPOINT 1
Show:
- Item counts per task (main and pilot).
- 3 examples per task.
- Gold label distributions.
- Manifold: count after each filter step, plus the cutoff date used.
- The `PREREG.md` diff.
- The updated planner estimate.

---

## Phase 2: Pilot

Run all pilot sets (20 per task) on all models in both modes.

Check:
- the parse rate per model × mode;
- reasoning-token leaks in gut mode;
- actual tokens and cost per item, which updates the planner;
- prompt cache hit rates on the long-option tasks;
- latency.

Allowed fixes: formatting and parsing, in **templates only** (log every change). No changes based on accuracy.

### CHECKPOINT 2
Show:
- Pilot health table.
- 2 raw outputs per mode per task.
- Template changes made.
- The updated cost estimate for the full run.

**Go/no-go on spend:** if the estimate is above the soft budget, propose cuts (fewer items on the big tasks, dropping `gpt-oss`, shrinking the large-model subset) before running.

---

## Phase 3: Full runs

- Fill the queue: 3 main models × all items × 2 modes, plus the large model × 50 items per task × 2 modes, plus `gpt-oss` if kept.
- `gch run` processes jobs in **random order** (so a partial run isn't biased), with concurrency limits per provider and backoff on rate limits.
- `gch status` shows progress by task, model and mode; spend so far; and projected total.

**Don't:** look at accuracy until the queue is complete. Status shows counts and cost only.

### CHECKPOINT 3
Show:
- Queue complete.
- Total spend vs estimate.
- Parse, leak and error summary per model × mode.

---

## Phase 4: Analysis and verdict cards

1. Compute all metrics per task × model × mode, with CIs.
2. Threshold search at p = 0.99 and 0.95.
3. Run the verdict rules, producing a **verdict card** per task (`reports/verdicts/<task>.md` + `.json`):
   - recommended configuration;
   - fast vs reasoned (accuracy, cost, latency);
   - the auto-accept threshold and coverage;
   - the overthinking flag;
   - a cost-accuracy frontier chart (every model × mode as a point, with cost per 1,000 items on the x-axis and accuracy on the y-axis).
4. Reliability diagrams per task (gut vs reasoned overlaid), and flip charts.

### CHECKPOINT 4
Show all 5 verdict cards, the frontier charts and reliability diagrams, plus any verdict that looks surprising, with the numbers behind it.

---

## Phase 5: Cross-task findings

1. **H1:** gut overconfidence, grammar vs forecasting (the difference with a CI), per model.
2. **H2:** reasoning gain and cost per extra correct answer, across all tasks. Where is reasoning worth paying for, and where not?
3. **H3 (forecasting):** correlation of gut vs reasoned probabilities with the crowd; follow rates on crowd-confident-wrong questions (crowd ≥ 70% on the losing side). Grammar: model accuracy vs human agreement per paradigm.
4. **Large vs small:** does the large model's gut behave like the small models' reasoning?

Write `reports/findings.md`: H1–H3 as **supported / not supported / mixed**, with CIs. Label any non-pre-registered analysis "exploratory".

### CHECKPOINT 5
Show the findings write-up and its charts.

---

## Phase 6: "Bring your own task" + drift (the product part)

1. **`gch new-task`:** turn a client-style CSV (text column, label column, optional label list) into a task pack. It infers `single_choice` vs `binary`, splits a pilot, and runs the planner. Test it on a small public CSV that wasn't used above (for example a news-topic dataset such as AG News, 100 rows) **end to end**: build → pilot → run → verdict card.
2. **`gch rerun --task X`:** rerun a stored task on the same items and compare with the saved baseline. Flag a **drift alert** if accuracy changes beyond the bootstrap CI, or if precision above the saved threshold drops below target. Test it by rerunning one task with a different model ID standing in for a "new version".

### CHECKPOINT 6
Show the AG News run end to end, including its verdict card, plus the drift report from the simulated version change.

---

## Phase 7 (optional): Jev arm

Only if access exists:
- implement `arms/jev.py`;
- run grammar, toxicity and forecasting natively, and Banking77/LEDGAR shortlisted (top 32 by embedding);
- report shortlist recall;
- add Jev as an extra point on each frontier chart and an extra row in each verdict card, labelled "decision model, native probabilities".

**Key question:** are native probabilities better calibrated than stated confidence, and at what cost?

### CHECKPOINT 7
Show the Jev results table, the calibration comparison and shortlist recall.

---

## Phase 8: Demo page (GitHub Pages)

`docs/index.html`, single file, data from `reports/*.json`:
1. **The hook:** one verdict card in full (Banking77), in plain words: what to run, where to auto-accept, and how much human review it saves.
2. **"Gut vs reasoned"** explained with one item per task: the gut answer, the reasoned answer and the truth, including one overthinking flip.
3. **Cost-accuracy frontier** per task (pick a task from a dropdown).
4. **Can you trust the confidence?** Reliability diagrams, kind (grammar) vs wicked (forecasting) side by side.
5. **Mirror vs oracle:** gut vs crowd on forecasting.
6. **Bring your own task:** the AG News example and the CLI command, framed as "this is what a client gets".
7. **Uses:**
   - mode advisor for LLM pipelines;
   - human-review sizing for ops;
   - model risk validation evidence;
   - drift monitoring.
8. **Limits:**
   - stated confidence ≠ true probability;
   - cheap-tier models plus one large model;
   - one prompt template;
   - public datasets may be in training data (BLiMP, Banking77, LEDGAR);
   - play-money crowd on Manifold;
   - gpt-oss has no true thinking-off.
9. Credits and licences for all datasets.

### CHECKPOINT 8
Page renders offline, every number comes from `reports/`, the limits are visible, and verdict cards on the page match `reports/verdicts/`.

---

## Size and cost

| | Calls (approx.) |
|---|---|
| Pilot: 100 items × 4–5 models × 2 modes | 800–1,000 |
| Main: 850 items × 3 models × 2 modes | ~5,100 |
| Large model: 250 items × 2 modes | 500 |
| `gpt-oss` (optional): 850 × 2 | 1,700 |
| AG News demo task: 100 × 3 × 2 | 600 |
| **Total** | **~7,000–8,900** |

Gut calls are tiny (about 20 output tokens). Cost is dominated by thinking tokens and the long option lists (softened by caching). The expected total is **roughly $10–25**; the Phase 0 and Phase 2 planners give the real figure before the big run.

## Rough timeline

| Phase | Time |
|---|---|
| 0 Setup + probe | 1 day |
| 1 Task packs + prereg | 1–1½ days |
| 2 Pilot | ½ day |
| 3 Full runs | ½–1 day (mostly waiting) |
| 4 Verdict cards | 1 day |
| 5 Cross-task findings | ½–1 day |
| 6 Bring your own task + drift | 1 day |
| 7 Jev (optional) | ½–1 day |
| 8 Demo page | 1 day |

About **7–8 working days** without Jev.

## Out of scope (v1)
- Live routing in production pipelines (the harness advises; it doesn't route).
- Free-text or generative tasks (they need a judge; v2).
- Effort-level sweeps beyond off vs on (for example low/medium/high ladders; v2).
- Temperature or prompt-style sweeps, fine-tuning, logprob-based confidence (optional v2 for models that expose it).
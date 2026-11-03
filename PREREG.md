# Pre-registration — Gut-Check Harness, lean v1

Written 2026-11-03, **before** any main-set item was run. Committed to git before `gch run`.
Pilot results were used only for parse health, token usage and cost; pilot accuracy was not inspected.

## Scope (deviations from README, decided before data)

| README full plan | Lean v1 |
|---|---|
| 5 tasks (BLiMP, Manifold, Banking77, LEDGAR, toxicity) | 3 tasks: **Banking77, BLiMP, toxicity** (Civil Comments) |
| 3 cheap models + 1 large + gpt-oss | **gpt-5.4-mini, claude-haiku-4-5** |
| Target precision 0.99 (0.95 also reported) | **0.95 primary**. 0.99 is reported but is mathematically unreachable here: the Wilson 95% lower bound needs ≥ 381 all-correct items above the threshold, and each task has 200 items. |
| 150–200 items/task | 200 main + 10 pilot per task, disjoint |

Modes: gut = `reasoning_effort: none` (gpt-5.4-mini) / no extended thinking (Haiku). Reasoned = `reasoning_effort: medium` / thinking with `budget_tokens: 2048`. The probe (`runs/probe.json`) confirmed 0 reasoning tokens in gut mode for both.

## Hypotheses

- **H1 (calibration, kind vs noisy):** gut-mode overconfidence (mean confidence − accuracy) is **lower on BLiMP** (regular grammar) **than on toxicity** (subjective, noisy gold labels), for each model. Tested as the difference with a bootstrap 95% CI. Supported if the CI excludes 0 in the predicted direction for both models; mixed if for one.
- **H2 (reasoning value):** on **toxicity and Banking77**, the verdict rule returns **"Use fast mode"** (the reasoned − gut accuracy CI includes 0, or gain < 1 point) for both models. Supported if all 4 task × model cells say fast; mixed if 2–3; not supported if 0–1.
- **H3 (confidence usable):** in **gut** mode, a safe auto-accept threshold at 95% precision with **coverage ≥ 30%** exists on **BLiMP and Banking77** for at least one model each.

Everything else is **exploratory** and will be labelled so.

## Metrics (per task × model × mode)

- **Accuracy**, 95% bootstrap CI over items (2,000 resamples, seed 20261103). Parse failures count as **incorrect** (primary). A sensitivity analysis excludes them.
- **Reasoned − gut accuracy**: paired bootstrap CI over items.
- **Cost per 1,000 items** from logged token usage × registry prices (`src/gch/models.py`). **Latency**: median and p90.
- **Calibration**: ECE with 10 equal-width bins on stated confidence/100. Reliability table. Overconfidence = mean confidence − accuracy (parsed items).
- **Flips** (same item, gut vs reasoned): right→wrong (overthinking), wrong→right (fix), wrong→wrong changed, unchanged.

## Threshold method

Lowest stated confidence *t* such that, among parsed items with confidence ≥ *t*, the **Wilson 95% lower bound** on precision is ≥ the target (0.95), with **≥ 30 items** above *t*. Coverage = items above *t* ÷ all items (parse failures in the denominator, never auto-accepted). If no such *t*: "no safe threshold".

## Verdict rules (`src/gch/verdict.py`, unit-tested)

- **Use fast mode** if the reasoned − gut CI includes 0 **or** the gain is < 1 point. Otherwise **Use reasoning**, with cost per extra correct answer = (reasoned − gut cost per item) ÷ accuracy gain.
- **Overthinking risk** if right→wrong ≥ 3% of items **or** ≥ 30% of all flips.
- **Confidence usable** if a safe threshold exists with coverage ≥ 30%. Otherwise: "send everything to review, or don't use confidence".
- **Cheapest configuration meeting target**: (a) lowest cost per 1k with accuracy CI lower bound ≥ the task's target accuracy (Banking77 0.90, BLiMP 0.95, toxicity 0.90); (b) the configuration whose auto-accept set meets 95% precision with the highest coverage (ties → cheaper). Both shown.

## Exclusions and handling

- Unparseable output gets one retry. After that it is `parse_fail`, counted and reported per model × mode.
- API errors are retried with backoff. Items that still error are re-queued on the next run. Any item still missing at analysis time is reported.
- Gut-mode reasoning leaks (reasoning tokens > 0) are flagged. If any occur, results are analysed with and without the leaking items.
- No prompt, template or rule changes after the main run starts. Pilot items are never reused.

---

# Addendum v1.1: confirmation study (written 2026-11-03, before any confirmation item was run)

Status at time of writing: the lean v1 main run (200 items/task, gpt-5.4-mini + claude-haiku-4-5) is complete, and its results are in `reports/`. Exploratory analysis of those 200 items (the **discovery set**) suggested the hypotheses below. They are tested on a **confirmation set** of 600 new items per task (`tasks/<task>/confirm.jsonl`, seed 20261104), disjoint from main and pilot by id and text. No confirmation item has been sent to any model before this addendum is committed.

## Changes

- **Third vendor:** `gemini-3.5-flash` (gut = `thinkingBudget: 0`, verified 0 thought tokens. Reasoned = default dynamic thinking). The README's `gemini-3.8-flash` was rejected because it has no true thinking-off: the probe on 2026-11-03 found 0–72 thought tokens at its lowest setting. Gemini is also run on the 200-item discovery set, so all three models have discovery data.
- **Budget:** soft budget raised to $40 (user-approved).
- Prompt template, parsing, the 95% precision target, the Wilson method and all v1 rules are unchanged. The v1 verdict cards are regenerated on the confirmation set exactly as before.

## Auto-accept policies (defined now, fitted on discovery, tested on confirmation)

For each task, an **auto-accept policy** decides which items skip human review and what answer to use:

- **SELF(m, mode, c):** accept if model *m* in *mode* states confidence ≥ c. Answer = its answer.
- **AGREE(S, mode, c):** for a set S of 2 or 3 models in the same mode, accept if **all models in S give the same answer** and each states confidence ≥ c. Answer = the shared answer. Pairs {gpt, haiku}, {gpt, gemini}, {haiku, gemini} and the triple, in gut and in reasoned mode.
- **MAJ(mode, c):** at least 2 of the 3 models agree, and each agreeing model states confidence ≥ c. Answer = the majority answer.

Confidence floors c ∈ {0, 50, 60, 70, 80, 85, 90, 95, 100}.

**Fitting (discovery set, n = 200):** for each policy, pick the lowest c with **point precision ≥ 97%** and ≥ 30 accepted items. A policy with no such c is "not fitted".
**Testing (confirmation set, n = 600):** apply the fitted c unchanged. A policy **passes** if the Wilson 95% lower bound on its precision is ≥ 0.95 (≥ 30 accepted). Report coverage = accepted ÷ 600.
**API cost of a policy** = the sum of the per-item costs of every call it uses (measured on the confirmation set).

**Review economics (pre-specified cost model):** total cost per 1,000 items = API cost + R × (items not accepted) + E × (accepted items that are wrong). Primary: R = $0.25 per human review, E = $2.50 per wrong auto-accepted answer. Sensitivity grid: R ∈ {0.05, 0.25, 1.00}, E ∈ {0, 2.50, 25}.

## Hypotheses

- **H4 (agreement beats self-confidence):** on **BLiMP and Banking77**, the best passing **gut-mode** AGREE/MAJ policy has **coverage ≥** the best passing SELF policy (any model, either mode; counted as 0 if none passes) **and lower API cost per 1,000 items**. Supported if this holds on both tasks, mixed if on one, not supported if on neither.
- **H5 (confidence is blind to human ambiguity):** on **toxicity**, items are "split" if the annotator toxicity score is 0.3–0.7, otherwise "clear". For each model in gut mode, accuracy on split items is lower than on clear items (bootstrap 95% CI of the difference excludes 0). But mean stated confidence is **not** lower: the CI of (split − clear) confidence includes 0 or lies above it. Supported if both parts hold for ≥ 2 of 3 models.
- **H6 (models agree with each other, not with the labels):** on **toxicity**, precision among items where all three gut answers agree is **< 85%**, and **no** policy (SELF, AGREE or MAJ, either mode) passes at 95% on the confirmation set.
- **H7 (thinking doesn't help on judgment tasks):** on **toxicity**, the v1 verdict rule returns "Use fast mode" for **all three** models on the confirmation set.

Replications of H1 to H3 on the confirmation set are reported as secondary results. Anything else is exploratory.

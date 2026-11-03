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

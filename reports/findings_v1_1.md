# Findings, v1.1 confirmation study (2026-11-04)

**Design.** Hypotheses H4–H7 were pre-registered (PREREG.md, Addendum v1.1, commit `59fae64`) before any confirmation item was run. Thresholds and rules were fitted on the 200-item discovery set, then applied unchanged to **600 new items per task**. Three vendors' cheap tier (gpt-5.4-mini, claude-haiku-4-5, gemini-3.5-flash), each in gut and reasoned mode.

10,800 confirmation calls with 0 errors, 0 parse failures, 0 gut-mode thinking leaks and 0 truncations. Spend for the confirmation run: $15.67 (estimate $20.07). Project total: **$21.35**.

Full tables: `reports/confirm/confirm_results.md`. Verdict cards: `reports/confirm/verdicts/`. Policy chart: `reports/confirm/policies.html`.

## Pre-registered hypotheses

| | Prediction | Result |
|---|---|---|
| H4 | Two or three cheap gut answers that agree beat self-confidence for auto-accept (BLiMP, Banking77) | **Not supported.** BLiMP: the best gut agreement policy covers 88% at $0.76/1k, but Gemini reasoned alone covers 100% at 98.0% precision. Banking77: no gut agreement policy passes. |
| H5 | On toxicity, confidence doesn't drop on items human annotators split on, though accuracy does | **Not supported as stated.** Haiku and Gemini confidence drops 3–4 pts on split items (CI excludes 0). gpt-5.4-mini's *rises* 2.7 pts, but its accuracy drop isn't significant. |
| H6 | On toxicity, three agreeing vendors are < 85% right, and no policy passes | **Not supported (narrowly).** When all three gut answers agree (81% of items) they are right 85.6% of the time, just over the 85% line. No policy passes at 95%. |
| H7 | Thinking doesn't help on toxicity, for any vendor | **Supported.** Fast mode for all 3. Haiku gets *worse* with thinking: −4.5 pts (CI −7.3 to −1.8), breaking 53 right answers while fixing 26. |

Replications of v1 hypotheses on the 600 new items:
- **H1** (gut more overconfident on toxicity than grammar) replicates for gpt-5.4-mini and gemini, but not for Haiku.
- **H2** (fast mode enough on toxicity and Banking77): toxicity replicates for all 3. Banking77 is now fast mode for Haiku and Gemini. Only gpt-5.4-mini still gains from thinking (+3.7 pts).
- **H3** (gut confidence usable): it now works on BLiMP for gpt and Haiku, and still fails on Banking77.

## What held up (the defensible client story)

1. **Thinking doesn't pay on judgment tasks, confirmed across three vendors.** On content moderation, reasoned mode costs 1.2–6× more and never improves accuracy. For Haiku it makes moderation measurably worse. All three trip the overthinking flag (right → wrong ≥ 3% of items).
2. **The same three models give very different safe automation depending on the task.** Using rules fitted on discovery data and checked on 600 new items:

   | Task | Best safe auto-accept (≥ 95% precision, lower bound) | Total cost / 1k items incl. review* | vs. all-human $250 |
   |---|---|---|---|
   | Grammar (BLiMP) | 92–100% of items (e.g. gpt+gemini reasoned agreeing: 96% at 99.0%) | **$41** | −84% |
   | Banking intents | **20%** (Gemini reasoned at confidence 100) | $209 | −16% |
   | Moderation | **0%**: no configuration is safe | $250 | 0% |

   *$0.25 per human review, $2.50 per wrong auto-accepted answer (pre-specified).
   Model price is noise next to review cost: API spend is $0.40–8 per 1k items, against $250 for human review.
3. **A threshold that looks safe on a small sample often isn't.** Of 27 auto-accept rules that hit ≥ 97% precision on the 200-item discovery set, **12 failed** the 95% bar on new data. On Banking77, **9 of 10 failed**. A vendor who sets a confidence cut-off on a few hundred examples is likely to over-promise on harder tasks.
4. **Our own exploratory headlines didn't survive.** "Agreement beats self-confidence" and "Haiku needs reasoning on Banking77" (+7 pts on discovery, +0.7 on confirmation) looked strong on 200 items and failed on 600. That is the case for the harness's method: pre-register, then confirm on held-out data before telling a client anything.

## Caveats

- Public datasets that may be in training data. One prompt template. Stated confidence, not logprobs.
- Gemini prices come from third-party aggregators, not Google's page.
- The review-cost figures are assumptions. The ranking holds across the pre-specified sensitivity grid (R $0.05–1.00, E $0–25), but the dollar amounts don't transfer.
- Toxicity gold is "≥ 50% of annotators". Part of the moderation "error" is policy mismatch, not model failure.

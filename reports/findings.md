# Findings — lean v1 (2026-11-03)

3 tasks × 200 items × 2 models (gpt-5.4-mini, claude-haiku-4-5) × 2 modes (gut / reasoned) = 2,400 calls.
0 errors, 0 parse failures, 0 gut-mode reasoning leaks, 0 truncations. Spend: **$3.13** for the main run (estimate $3.51); $3.29 in total including probe and pilot.
Verdict cards: `reports/verdicts/<task>.md`. Hypotheses as pre-registered in `PREREG.md` (commit `35972ed`, pushed before the main run).

## Verdicts at a glance

| Task | gpt-5.4-mini | claude-haiku-4-5 | Auto-accept at 95% precision |
|---|---|---|---|
| Banking77 (77 intents) | **Use reasoning**: +6.5 pts (CI +2.0 to +11.5), 1.6× cost | **Use reasoning**: +7.0 pts (CI +2.5 to +12.0), 1.8× cost | None safe |
| BLiMP (grammar A/B) | **Use reasoning**: +9.5 pts (CI +4.5 to +14.5), 9.1× cost | **Fast mode** (+3.0 pts, CI lower bound 0.0, borderline) | Haiku reasoned, confidence ≥ 87 → **72% coverage** |
| Toxicity (Civil Comments) | **Fast mode** (+2.0, CI −3.0 to +7.0) | **Fast mode** (−4.0, CI −8.5 to +0.5) | None safe |

The overthinking flag is raised on Banking77 (both models, 3.0%) and toxicity (both: Haiku 7.5%, gpt-5.4-mini 5.0% right → wrong).

No configuration reaches its task's target accuracy (CI lower bound ≥ 90% / 95% / 90%). The best accuracies are 82.5% on Banking77 and 74% on toxicity (gpt-5.4-mini reasoned), and 96.0% on BLiMP (gpt-5.4-mini reasoned, CI 93.0–98.5).

## Pre-registered hypotheses

- **H1, gut overconfidence lower on BLiMP than toxicity: SUPPORTED.** The toxicity − BLiMP difference in gut overconfidence is +8.6 pts for Haiku (95% CI +1.6 to +15.4) and +9.7 pts for gpt-5.4-mini (CI +2.1 to +17.7). Haiku's gut confidence on grammar is almost perfectly calibrated (ECE 0.007, overconfidence +0.6 pts).
- **H2, fast mode on toxicity and Banking77: MIXED (2 of 4 cells).** Toxicity says fast mode for both models, as predicted. Banking77 says use reasoning for both: about +7 pts at under 2× the cost.
- **H3, gut-mode confidence usable on BLiMP and Banking77: NOT SUPPORTED.** No gut configuration has a safe 95% threshold with ≥ 30% coverage on any task. The only usable threshold is Haiku **reasoned** on BLiMP.

## Exploratory (not pre-registered)

- **Reasoning fixes calibration more than accuracy.** On Banking77, ECE roughly halves with thinking (0.177 → 0.087 for gpt-5.4-mini, 0.141 → 0.087 for Haiku). On BLiMP, reasoned mode becomes slightly *under*confident (−5 pts).
- **Toxicity errors are mostly over-flagging.** Across the four configurations, 38–48 of the 140 non-toxic comments were called toxic, against 7–17 of the 60 toxic ones missed. The models are stricter than Civil Comments' "≥ 50% of annotators" label. Part of the "wicked" behaviour here is label noise, not model error. A client with its own moderation policy would get different numbers.
- **Haiku reasoned is the slow option**: a median of 3.5–4.8 s against about 1 s for gut mode. gpt-5.4-mini reasoned adds only about 0.3–0.7 s.

## Caveats

- Stated confidence is not a true probability. One prompt template. n = 200 per task, so CIs are about ±6 pts.
- BLiMP and Banking77 may be in training data.
- The Haiku BLiMP "fast mode" verdict sits exactly on the CI boundary (lower bound 0.0). The rule treats a bound of 0 as "includes 0".
- Haiku thinking-token counts are estimates (output tokens − visible answer). Its costs come from billed tokens and are exact.
- The 99% precision target is unreachable with 200 items (it needs ≥ 381 all-correct items above the threshold), so it is reported as "none" everywhere.

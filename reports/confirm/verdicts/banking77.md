# Verdict card: Banking77 intent classification

## Recommendation
- **No configuration's accuracy CI lower bound reaches 90%.**
- **No configuration has a safe auto-accept threshold at 95% precision with ≥30% coverage.** Send everything to review, or don't use confidence.

### `claude-haiku-4-5`: Use fast mode
Thinking changes accuracy by +0.7 pts (95% CI -1.5 to +2.8) at 1.7× the cost (accuracy gain CI includes 0).
Flips: 23 fixed, **19 overthought** (right → wrong, 3.2% of items), 20 wrong → different wrong. **⚠ Overthinking risk.**

### `gemini-3.5-flash`: Use fast mode
Thinking changes accuracy by +1.0 pts (95% CI -0.8 to +2.8) at 2.8× the cost (accuracy gain CI includes 0).
Flips: 19 fixed, **13 overthought** (right → wrong, 2.2% of items), 12 wrong → different wrong.

### `gpt-5.4-mini`: Use reasoning
Thinking changes accuracy by +3.7 pts (95% CI +1.7 to +5.8) at 1.5× the cost (+3.7 pts, CI excludes 0). Cost per extra correct answer: $0.0117.
Flips: 33 fixed, **11 overthought** (right → wrong, 1.8% of items), 14 wrong → different wrong.

## Fast vs reasoned, all configurations
| Model | Mode | Accuracy (95% CI) | $ / 1k items | Latency median / p90 | Thinking tok/item | ECE | Overconfidence | Auto-accept @95% (coverage) | @99% | Parse fails |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-4-5 | gut | 78.2% (74.8%–81.5%) | $1.77 | 1.6s / 3.8s | 0 | 0.087 | +8.6 pts | none | none | 0 |
| claude-haiku-4-5 | reasoned | 78.8% (75.7%–82.2%) | $3.07 | 4.6s / 8.3s | 257 | 0.083 | +8.2 pts | none | none | 0 |
| gemini-3.5-flash | gut | 83.2% (80.2%–86.2%) | $1.26 | 1.9s / 4.4s | 0 | 0.125 | +12.5 pts | none | none | 0 |
| gemini-3.5-flash | reasoned | 84.2% (81.2%–87.0%) | $3.50 | 3.2s / 6.6s | 249 | 0.118 | +11.8 pts | ≥99 (20%) | none | 0 |
| gpt-5.4-mini | gut | 80.3% (77.2%–83.5%) | $0.85 | 1.5s / 3.7s | 0 | 0.139 | +13.9 pts | none | none | 0 |
| gpt-5.4-mini | reasoned | 84.0% (81.0%–87.0%) | $1.28 | 1.9s / 4.1s | 89 | 0.082 | +8.2 pts | none | none | 0 |

Notes: n = 600 items. Parse failures count as wrong. The 99% target needs ≥381 all-correct items above the threshold, so with this sample it is expected to show 'none'. Haiku thinking tokens are estimated (output − visible answer).

Charts: `frontier_<task>.html` (cost vs accuracy), `reliability_<task>.html` (calibration).
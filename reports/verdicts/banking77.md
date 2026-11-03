# Verdict card: Banking77 intent classification

## Recommendation
- **No configuration's accuracy CI lower bound reaches 90%.**
- **Best auto-accept set at 95% precision:** `gemini-3.5-flash` · **gut**, accept when confidence ≥ 100: covers **44%** of items; the rest go to human review ($1.26 per 1k).

### `claude-haiku-4-5`: Use reasoning
Thinking changes accuracy by +7.0 pts (95% CI +2.5 to +12.0) at 1.8× the cost (+7.0 pts, CI excludes 0). Cost per extra correct answer: $0.0205.
Flips: 20 fixed, **6 overthought** (right → wrong, 3.0% of items), 7 wrong → different wrong. **⚠ Overthinking risk.**

### `gemini-3.5-flash`: Use fast mode
Thinking changes accuracy by +1.5 pts (95% CI -0.5 to +4.0) at 2.8× the cost (accuracy gain CI includes 0).
Flips: 4 fixed, **1 overthought** (right → wrong, 0.5% of items), 8 wrong → different wrong.

### `gpt-5.4-mini`: Use reasoning
Thinking changes accuracy by +6.5 pts (95% CI +2.0 to +11.5) at 1.6× the cost (+6.5 pts, CI excludes 0). Cost per extra correct answer: $0.0075.
Flips: 19 fixed, **6 overthought** (right → wrong, 3.0% of items), 6 wrong → different wrong. **⚠ Overthinking risk.**

## Fast vs reasoned, all configurations
| Model | Mode | Accuracy (95% CI) | $ / 1k items | Latency median / p90 | Thinking tok/item | ECE | Overconfidence | Auto-accept @95% (coverage) | @99% | Parse fails |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-4-5 | gut | 70.0% (63.5%–76.0%) | $1.77 | 1.0s / 1.5s | 0 | 0.141 | +14.1 pts | none | none | 0 |
| claude-haiku-4-5 | reasoned | 77.0% (71.0%–82.5%) | $3.21 | 3.5s / 6.4s | 285 | 0.087 | +8.2 pts | none | none | 0 |
| gemini-3.5-flash | gut | 83.0% (77.5%–87.5%) | $1.26 | 1.7s / 3.1s | 0 | 0.125 | +12.5 pts | ≥100 (44%) | none | 0 |
| gemini-3.5-flash | reasoned | 84.5% (79.0%–89.5%) | $3.50 | 3.2s / 5.3s | 249 | 0.112 | +11.2 pts | none | none | 0 |
| gpt-5.4-mini | gut | 76.0% (70.0%–81.5%) | $0.85 | 1.0s / 1.3s | 0 | 0.177 | +17.7 pts | none | none | 0 |
| gpt-5.4-mini | reasoned | 82.5% (77.5%–87.5%) | $1.34 | 1.3s / 2.1s | 102 | 0.087 | +8.7 pts | none | none | 0 |

Notes: n = 200 items. Parse failures count as wrong. The 99% target needs ≥381 all-correct items above the threshold, so with this sample it is expected to show 'none'. Haiku thinking tokens are estimated (output − visible answer).

Charts: `frontier_<task>.html` (cost vs accuracy), `reliability_<task>.html` (calibration).
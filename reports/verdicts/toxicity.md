# Verdict card: Toxicity (Civil Comments)

## Recommendation
- **No configuration's accuracy CI lower bound reaches 90%.**
- **No configuration has a safe auto-accept threshold at 95% precision with ≥30% coverage.** Send everything to review, or don't use confidence.

### `claude-haiku-4-5`: Use fast mode
Thinking changes accuracy by -4.0 pts (95% CI -8.5 to +0.5) at 5.1× the cost (accuracy gain CI includes 0).
Flips: 7 fixed, **15 overthought** (right → wrong, 7.5% of items), 0 wrong → different wrong. **⚠ Overthinking risk.**

### `gemini-3.5-flash`: Use fast mode
Thinking changes accuracy by +1.5 pts (95% CI -2.5 to +5.5) at 6.0× the cost (accuracy gain CI includes 0).
Flips: 10 fixed, **7 overthought** (right → wrong, 3.5% of items), 0 wrong → different wrong. **⚠ Overthinking risk.**

### `gpt-5.4-mini`: Use fast mode
Thinking changes accuracy by +2.0 pts (95% CI -3.0 to +7.0) at 2.3× the cost (accuracy gain CI includes 0).
Flips: 14 fixed, **10 overthought** (right → wrong, 5.0% of items), 0 wrong → different wrong. **⚠ Overthinking risk.**

## Fast vs reasoned, all configurations
| Model | Mode | Accuracy (95% CI) | $ / 1k items | Latency median / p90 | Thinking tok/item | ECE | Overconfidence | Auto-accept @95% (coverage) | @99% | Parse fails |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-4-5 | gut | 72.5% (66.0%–78.5%) | $0.45 | 0.9s / 1.3s | 0 | 0.111 | +9.2 pts | none | none | 0 |
| claude-haiku-4-5 | reasoned | 68.5% (62.0%–75.0%) | $2.28 | 4.7s / 6.7s | 365 | 0.104 | +10.4 pts | none | none | 0 |
| gemini-3.5-flash | gut | 78.5% (72.5%–84.0%) | $0.38 | 1.9s / 3.5s | 0 | 0.114 | +11.4 pts | none | none | 0 |
| gemini-3.5-flash | reasoned | 80.0% (74.5%–85.5%) | $2.25 | 3.0s / 5.1s | 209 | 0.111 | +10.7 pts | none | none | 0 |
| gpt-5.4-mini | gut | 72.0% (65.5%–78.5%) | $0.23 | 1.0s / 1.3s | 0 | 0.191 | +18.8 pts | none | none | 0 |
| gpt-5.4-mini | reasoned | 74.0% (68.0%–80.0%) | $0.53 | 1.2s / 1.7s | 61 | 0.184 | +18.4 pts | none | none | 0 |

Notes: n = 200 items. Parse failures count as wrong. The 99% target needs ≥381 all-correct items above the threshold, so with this sample it is expected to show 'none'. Haiku thinking tokens are estimated (output − visible answer).

Charts: `frontier_<task>.html` (cost vs accuracy), `reliability_<task>.html` (calibration).
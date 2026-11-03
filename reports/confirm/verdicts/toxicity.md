# Verdict card: Toxicity (Civil Comments)

## Recommendation
- **No configuration's accuracy CI lower bound reaches 90%.**
- **No configuration has a safe auto-accept threshold at 95% precision with ≥30% coverage.** Send everything to review, or don't use confidence.

### `claude-haiku-4-5`: Use fast mode
Thinking changes accuracy by -4.5 pts (95% CI -7.3 to -1.8) at 5.2× the cost (gain < 1 point).
Flips: 26 fixed, **53 overthought** (right → wrong, 8.8% of items), 0 wrong → different wrong. **⚠ Overthinking risk.**

### `gemini-3.5-flash`: Use fast mode
Thinking changes accuracy by -0.2 pts (95% CI -2.3 to +2.0) at 5.9× the cost (accuracy gain CI includes 0).
Flips: 21 fixed, **22 overthought** (right → wrong, 3.7% of items), 0 wrong → different wrong. **⚠ Overthinking risk.**

### `gpt-5.4-mini`: Use fast mode
Thinking changes accuracy by +0.2 pts (95% CI -2.5 to +2.7) at 2.3× the cost (accuracy gain CI includes 0).
Flips: 32 fixed, **31 overthought** (right → wrong, 5.2% of items), 0 wrong → different wrong. **⚠ Overthinking risk.**

## Fast vs reasoned, all configurations
| Model | Mode | Accuracy (95% CI) | $ / 1k items | Latency median / p90 | Thinking tok/item | ECE | Overconfidence | Auto-accept @95% (coverage) | @99% | Parse fails |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-4-5 | gut | 78.8% (75.5%–82.0%) | $0.45 | 1.6s / 4.0s | 0 | 0.055 | +2.3 pts | none | none | 0 |
| claude-haiku-4-5 | reasoned | 74.3% (70.8%–77.8%) | $2.31 | 6.1s / 9.8s | 371 | 0.075 | +4.7 pts | none | none | 0 |
| gemini-3.5-flash | gut | 80.8% (77.7%–83.8%) | $0.38 | 1.9s / 4.5s | 0 | 0.091 | +9.1 pts | none | none | 0 |
| gemini-3.5-flash | reasoned | 80.7% (77.5%–83.7%) | $2.23 | 3.3s / 6.5s | 205 | 0.105 | +10.5 pts | none | none | 0 |
| gpt-5.4-mini | gut | 77.5% (74.0%–80.7%) | $0.23 | 1.5s / 4.0s | 0 | 0.145 | +13.7 pts | none | none | 0 |
| gpt-5.4-mini | reasoned | 77.7% (74.3%–81.0%) | $0.53 | 1.6s / 4.1s | 61 | 0.143 | +14.3 pts | none | none | 0 |

Notes: n = 600 items. Parse failures count as wrong. The 99% target needs ≥381 all-correct items above the threshold, so with this sample it is expected to show 'none'. Haiku thinking tokens are estimated (output − visible answer).

Charts: `frontier_<task>.html` (cost vs accuracy), `reliability_<task>.html` (calibration).
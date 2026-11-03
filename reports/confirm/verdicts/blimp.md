# Verdict card: BLiMP grammaticality (A/B)

## Recommendation
- **Cheapest config meeting 95% accuracy (CI lower bound):** `gemini-3.5-flash` · **reasoned** at $3.10 per 1,000 items.
- **Best auto-accept set at 95% precision:** `gemini-3.5-flash` · **reasoned**, accept when confidence ≥ 80: covers **100%** of items; the rest go to human review ($3.10 per 1k).

### `claude-haiku-4-5`: Use fast mode
Thinking changes accuracy by +1.2 pts (95% CI -1.0 to +3.5) at 6.0× the cost (accuracy gain CI includes 0).
Flips: 25 fixed, **18 overthought** (right → wrong, 3.0% of items), 0 wrong → different wrong. **⚠ Overthinking risk.**

### `gemini-3.5-flash`: Use reasoning
Thinking changes accuracy by +3.5 pts (95% CI +1.8 to +5.2) at 9.0× the cost (+3.5 pts, CI excludes 0). Cost per extra correct answer: $0.0787.
Flips: 25 fixed, **4 overthought** (right → wrong, 0.7% of items), 0 wrong → different wrong.

### `gpt-5.4-mini`: Use reasoning
Thinking changes accuracy by +8.2 pts (95% CI +5.8 to +10.7) at 8.5× the cost (+8.2 pts, CI excludes 0). Cost per extra correct answer: $0.0188.
Flips: 54 fixed, **5 overthought** (right → wrong, 0.8% of items), 0 wrong → different wrong.

## Fast vs reasoned, all configurations
| Model | Mode | Accuracy (95% CI) | $ / 1k items | Latency median / p90 | Thinking tok/item | ECE | Overconfidence | Auto-accept @95% (coverage) | @99% | Parse fails |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-4-5 | gut | 92.7% (90.5%–94.7%) | $0.41 | 1.5s / 3.9s | 0 | 0.014 | +0.6 pts | ≥95 (61%) | none | 0 |
| claude-haiku-4-5 | reasoned | 93.8% (91.8%–95.7%) | $2.46 | 6.1s / 10.4s | 408 | 0.043 | -3.2 pts | ≥75 (86%) | ≥92 (72%) | 0 |
| gemini-3.5-flash | gut | 94.5% (92.7%–96.2%) | $0.34 | 1.8s / 4.3s | 0 | 0.046 | +4.6 pts | none | none | 0 |
| gemini-3.5-flash | reasoned | 98.0% (96.8%–99.0%) | $3.10 | 3.3s / 7.7s | 306 | 0.012 | +1.1 pts | ≥80 (100%) | ≥100 (84%) | 0 |
| gpt-5.4-mini | gut | 87.3% (84.5%–90.0%) | $0.20 | 1.5s / 3.3s | 0 | 0.084 | +8.4 pts | ≥99 (40%) | none | 0 |
| gpt-5.4-mini | reasoned | 95.5% (93.7%–97.0%) | $1.74 | 2.4s / 6.9s | 333 | 0.037 | -3.7 pts | ≥64 (92%) | none | 0 |

Notes: n = 600 items. Parse failures count as wrong. The 99% target needs ≥381 all-correct items above the threshold, so with this sample it is expected to show 'none'. Haiku thinking tokens are estimated (output − visible answer).

Charts: `frontier_<task>.html` (cost vs accuracy), `reliability_<task>.html` (calibration).
# Verdict card: BLiMP grammaticality (A/B)

## Recommendation
- **Cheapest config meeting 95% accuracy (CI lower bound):** `gemini-3.5-flash` · **reasoned** at $3.41 per 1,000 items.
- **Best auto-accept set at 95% precision:** `gemini-3.5-flash` · **reasoned**, accept when confidence ≥ 95: covers **97%** of items; the rest go to human review ($3.41 per 1k).

### `claude-haiku-4-5`: Use fast mode
Thinking changes accuracy by +3.0 pts (95% CI +0.0 to +6.5) at 6.1× the cost (accuracy gain CI includes 0).
Flips: 8 fixed, **2 overthought** (right → wrong, 1.0% of items), 0 wrong → different wrong.

### `gemini-3.5-flash`: Use reasoning
Thinking changes accuracy by +4.0 pts (95% CI +1.0 to +7.0) at 9.9× the cost (+4.0 pts, CI excludes 0). Cost per extra correct answer: $0.0767.
Flips: 9 fixed, **1 overthought** (right → wrong, 0.5% of items), 0 wrong → different wrong.

### `gpt-5.4-mini`: Use reasoning
Thinking changes accuracy by +9.5 pts (95% CI +4.5 to +14.5) at 9.1× the cost (+9.5 pts, CI excludes 0). Cost per extra correct answer: $0.0174.
Flips: 23 fixed, **4 overthought** (right → wrong, 2.0% of items), 0 wrong → different wrong.

## Fast vs reasoned, all configurations
| Model | Mode | Accuracy (95% CI) | $ / 1k items | Latency median / p90 | Thinking tok/item | ECE | Overconfidence | Auto-accept @95% (coverage) | @99% | Parse fails |
|---|---|---|---|---|---|---|---|---|---|---|
| claude-haiku-4-5 | gut | 92.0% (88.0%–95.5%) | $0.41 | 0.9s / 1.4s | 0 | 0.007 | +0.6 pts | none | none | 0 |
| claude-haiku-4-5 | reasoned | 95.0% (91.5%–98.0%) | $2.52 | 4.8s / 9.2s | 420 | 0.055 | -5.4 pts | ≥87 (72%) | none | 0 |
| gemini-3.5-flash | gut | 93.5% (90.0%–96.5%) | $0.34 | 1.8s / 3.7s | 0 | 0.049 | +4.4 pts | none | none | 0 |
| gemini-3.5-flash | reasoned | 97.5% (95.0%–99.5%) | $3.41 | 3.2s / 6.3s | 341 | 0.013 | +1.3 pts | ≥95 (97%) | none | 0 |
| gpt-5.4-mini | gut | 86.5% (81.5%–91.0%) | $0.20 | 1.0s / 1.3s | 0 | 0.116 | +9.1 pts | none | none | 0 |
| gpt-5.4-mini | reasoned | 96.0% (93.0%–98.5%) | $1.86 | 1.7s / 5.8s | 359 | 0.052 | -4.6 pts | none | none | 0 |

Notes: n = 200 items. Parse failures count as wrong. The 99% target needs ≥381 all-correct items above the threshold, so with this sample it is expected to show 'none'. Haiku thinking tokens are estimated (output − visible answer).

Charts: `frontier_<task>.html` (cost vs accuracy), `reliability_<task>.html` (calibration).
# v1.1 confirmation results

Thresholds and agreement rules were **fitted on the 200-item discovery set** and **tested unchanged on 600 new items per task**, as pre-registered (PREREG.md, Addendum v1.1). Pass = Wilson 95% lower bound on precision ≥ 95% with ≥ 30 items accepted. Total cost assumes $0.25 per human review and $2.50 per wrong auto-accepted answer.

## Hypotheses
- **H4: NOT SUPPORTED**
- **H5: NOT SUPPORTED**
- **H6: NOT SUPPORTED**
- **H7: SUPPORTED**

## Banking77 intent classification (n = 600)
Best self-confidence policy: **SELF(gemini, reasoned)** (coverage 20%). Best gut-mode agreement policy: **none passes** (coverage 0%).

| Policy | Floor (fit on discovery) | Coverage | Precision | Lower bound | Pass | API $/1k | Total $/1k incl. review |
|---|---|---|---|---|---|---|---|
| SELF(gemini, reasoned) | ≥100 | 20% | 99.2% | 95.4% | ✅ | $3.50 | $209 |
| AGREE(gpt+gemini, reasoned) | ≥95 | 59% | 93.5% | 90.5% | ❌ | $4.78 | $203 |
| SELF(gemini, gut) | ≥100 | 50% | 95.3% | 92.3% | ❌ | $1.26 | $184 |
| AGREE(gpt+haiku, reasoned) | ≥90 | 48% | 94.8% | 91.7% | ❌ | $4.35 | $196 |
| AGREE(gpt+haiku+gemini, reasoned) | ≥90 | 48% | 95.2% | 92.0% | ❌ | $7.85 | $196 |
| MAJ(gpt+haiku+gemini, reasoned) | ≥95 | 40% | 95.0% | 91.4% | ❌ | $7.85 | $209 |
| SELF(haiku, gut) | ≥95 | 22% | 97.7% | 93.5% | ❌ | $1.77 | $209 |
| AGREE(gpt+haiku, gut) | ≥95 | 22% | 97.7% | 93.4% | ❌ | $2.63 | $211 |
| AGREE(haiku+gemini, gut) | ≥95 | 22% | 98.5% | 94.6% | ❌ | $3.04 | $207 |
| AGREE(gpt+haiku+gemini, gut) | ≥95 | 21% | 98.4% | 94.5% | ❌ | $3.89 | $209 |

Not fitted on discovery (never reached 97% precision): SELF(gpt, gut), SELF(gpt, reasoned), SELF(haiku, reasoned), AGREE(gpt+gemini, gut), MAJ(gpt+haiku+gemini, gut), AGREE(haiku+gemini, reasoned).

Baseline, everything to human review: $250 per 1k items.

## BLiMP grammaticality (A/B) (n = 600)
Best self-confidence policy: **SELF(gemini, reasoned)** (coverage 100%). Best gut-mode agreement policy: **AGREE(haiku+gemini, gut)** (coverage 88%).

| Policy | Floor (fit on discovery) | Coverage | Precision | Lower bound | Pass | API $/1k | Total $/1k incl. review |
|---|---|---|---|---|---|---|---|
| SELF(gemini, reasoned) | ≥0 | 100% | 98.0% | 96.5% | ✅ | $3.10 | $53 |
| MAJ(gpt+haiku+gemini, reasoned) | ≥0 | 100% | 96.8% | 95.1% | ✅ | $7.30 | $86 |
| AGREE(gpt+gemini, reasoned) | ≥0 | 96% | 99.0% | 97.7% | ✅ | $4.84 | $41 |
| AGREE(haiku+gemini, reasoned) | ≥0 | 94% | 98.8% | 97.5% | ✅ | $5.56 | $49 |
| AGREE(gpt+haiku, reasoned) | ≥0 | 94% | 97.5% | 95.9% | ✅ | $4.20 | $78 |
| AGREE(gpt+haiku+gemini, reasoned) | ≥0 | 92% | 99.3% | 98.1% | ✅ | $7.30 | $44 |
| AGREE(haiku+gemini, gut) | ≥80 | 88% | 98.1% | 96.5% | ✅ | $0.76 | $73 |
| SELF(gpt, reasoned) | ≥80 | 85% | 98.4% | 96.9% | ✅ | $1.74 | $72 |
| SELF(haiku, reasoned) | ≥80 | 81% | 99.0% | 97.6% | ✅ | $2.46 | $70 |
| AGREE(gpt+gemini, gut) | ≥95 | 76% | 98.5% | 96.9% | ✅ | $0.55 | $89 |
| AGREE(gpt+haiku+gemini, gut) | ≥90 | 76% | 99.3% | 98.1% | ✅ | $0.96 | $75 |
| SELF(haiku, gut) | ≥95 | 61% | 99.2% | 97.6% | ✅ | $0.41 | $110 |
| MAJ(gpt+haiku+gemini, gut) | ≥95 | 61% | 98.9% | 97.2% | ✅ | $0.96 | $116 |
| AGREE(gpt+haiku, gut) | ≥95 | 57% | 99.7% | 98.4% | ✅ | $0.62 | $111 |
| SELF(gemini, gut) | ≥100 | 93% | 96.8% | 95.0% | ❌ | $0.34 | $92 |

Not fitted on discovery (never reached 97% precision): SELF(gpt, gut).

Baseline, everything to human review: $250 per 1k items.

## Toxicity (Civil Comments) (n = 600)
Best self-confidence policy: **none passes** (coverage 0%). Best gut-mode agreement policy: **none passes** (coverage 0%).

| Policy | Floor (fit on discovery) | Coverage | Precision | Lower bound | Pass | API $/1k | Total $/1k incl. review |
|---|---|---|---|---|---|---|---|
| SELF(gemini, gut) | ≥100 | 23% | 97.8% | 93.8% | ❌ | $0.38 | $205 |
| SELF(gemini, reasoned) | ≥100 | 18% | 96.2% | 90.7% | ❌ | $2.23 | $225 |

Not fitted on discovery (never reached 97% precision): SELF(gpt, gut), SELF(gpt, reasoned), SELF(haiku, gut), SELF(haiku, reasoned), AGREE(gpt+haiku, gut), AGREE(gpt+gemini, gut), AGREE(haiku+gemini, gut), AGREE(gpt+haiku+gemini, gut), MAJ(gpt+haiku+gemini, gut), AGREE(gpt+haiku, reasoned), AGREE(gpt+gemini, reasoned), AGREE(haiku+gemini, reasoned), AGREE(gpt+haiku+gemini, reasoned), MAJ(gpt+haiku+gemini, reasoned).

Baseline, everything to human review: $250 per 1k items.

## Toxicity: confidence vs human ambiguity (H5)
| Model | Accuracy, clear items | Accuracy, split items | Δ (95% CI) | Confidence, clear | Confidence, split | Δ (95% CI) |
|---|---|---|---|---|---|---|
| gpt-5.4-mini | 78.7% | 73.9% | -4.9 (-13.3, +3.0) | 90.5 | 93.2 | +2.7 (+1.6, +3.7) |
| claude-haiku-4-5 | 81.9% | 69.9% | -11.9 (-20.1, -3.9) | 82.0 | 78.6 | -3.4 (-4.6, -2.1) |
| gemini-3.5-flash | 87.7% | 60.8% | -26.9 (-35.3, -18.8) | 91.0 | 86.6 | -4.4 (-5.8, -2.9) |

**H6:** all three gut answers agree on 81% of toxicity items, but are right only 85.6% of the time when they do. Any policy passes: False.

**H7 (toxicity mode verdicts):** {'gpt-5.4-mini': 'Use fast mode', 'claude-haiku-4-5': 'Use fast mode', 'gemini-3.5-flash': 'Use fast mode'}

## Replications of v1 hypotheses on the confirmation set
- H1 gpt-5.4-mini: toxicity − BLiMP gut overconfidence +5.3 pts (CI +1.3 to +9.4)
- H1 claude-haiku-4-5: toxicity − BLiMP gut overconfidence +1.7 pts (CI -2.0 to +5.4)
- H1 gemini-3.5-flash: toxicity − BLiMP gut overconfidence +4.5 pts (CI +1.0 to +8.0)
- H2 mode verdicts: {'toxicity': {'gpt-5.4-mini': 'Use fast mode', 'claude-haiku-4-5': 'Use fast mode', 'gemini-3.5-flash': 'Use fast mode'}, 'banking77': {'gpt-5.4-mini': 'Use reasoning', 'claude-haiku-4-5': 'Use fast mode', 'gemini-3.5-flash': 'Use fast mode'}}
- H3 gut confidence usable: {'blimp': {'gpt-5.4-mini': True, 'claude-haiku-4-5': True, 'gemini-3.5-flash': False}, 'banking77': {'gpt-5.4-mini': False, 'claude-haiku-4-5': False, 'gemini-3.5-flash': False}}
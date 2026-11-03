# BLiMP task pack

- **Source:** BLiMP (Warstadt et al. 2020, TACL, arXiv:1912.00582), Hugging Face `nyu-mll/blimp`
  via the datasets-server API (https://datasets-server.huggingface.co/rows), one config per paradigm, split `train` (the only split).
  Original repo: https://github.com/alexwarstadt/blimp
- **Licence:** CC BY 4.0 (stated in the BLiMP repo README and the HF dataset card)
- **Date fetched:** 2026-11-03
- **Seed:** 20261103 (`random.Random(SEED)`, see `src/gch/build_tasks.py::build_blimp`)

## Candidate pool
- 67 paradigms; for each, the first 100 minimal pairs (rows 0–99
  of 1000) were downloaded. No other filters.

## Main (`items.jsonl`)
- Stratified across paradigms: 3 random pairs per paradigm, except one randomly chosen paradigm
  (`determiner_noun_agreement_irregular_1`) which gets 2 → 200 items. Order shuffled.
- A/B order: exactly half of items have the grammatical sentence as A (assignment shuffled with the seed).
  Gold balance: A = 100, B = 100.
- Field distribution: morphology 53, semantics 27, syntax 78, syntax/semantics 3, syntax_semantics 39.

## Pilot (`pilot.jsonl`)
- 10 distinct paradigms chosen at random, one pair each, drawn from rows **not** used in main and sharing
  **no sentence** (normalised) with any main item. Gold balance: A = 5, B = 5.
- Count: 10.

## Human agreement
- Attached: **yes** (67/67 paradigms).
- Source: official BLiMP repo file `raw_results/summary/human_validation_summary.csv`
  (https://raw.githubusercontent.com/alexwarstadt/blimp/master/raw_results/summary/human_validation_summary.csv). Column `total_mean` = mean human accuracy on that paradigm's validation pairs
  (forced-choice, 5 annotators per pair; `count` = pairs validated, 98–100). This is the human
  validation reported in Warstadt et al. (2020).
- Stored as top-level `human_ref` and `meta.human_agreement` (same value, per paradigm, not per item).
  Range across paradigms: 0.6063 – 0.99.

- Note: humans validated a subset of pairs per paradigm; it is not known whether those are the exact
  pairs sampled here, so treat `human_ref` as a paradigm-level difficulty indicator.

## Item format
`id` = `blimp-<paradigm>-<pair_id>`, `input` = `"A: <sentence>\nB: <sentence>"`, `gold` = `A`|`B`,
`meta` = {paradigm, pair_id, field, linguistics_term, human_agreement}.

# Banking77 task pack

- **Source:** PolyAI Banking77 — https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/test.csv and https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/train.csv
  (repo: https://github.com/PolyAI-LDN/task-specific-datasets; paper: Casanueva et al. 2020, arXiv:2003.04807)
- **Licence:** CC BY 4.0
- **Date fetched:** 2026-11-03
- **Seed:** 20261103 (`random.Random(SEED)`, see `src/gch/build_tasks.py::build_banking77`)
- **Options:** `options.txt` = the 77 intent labels exactly as in the dataset's `category` column, sorted alphabetically.

## Main (`items.jsonl`) — test split
- Filter: exact duplicate texts within test (case/whitespace-normalised) dropped, keeping the first occurrence.
- Sampling: stratified by intent. Every one of the 77 intents gets 2 items; the remaining
  46 items go to 46 distinct intents chosen at random (3 items each). Rows sampled uniformly within intent; order shuffled.
- Count: 200. Distribution: 31 intents × 2, 46 intents × 3.

## Pilot (`pilot.jsonl`) — train split
- 10 distinct intents chosen at random, one train row each, excluding any train text that also
  appears (normalised) anywhere in the test split.
- Count: 10. Intents: apple_pay_or_google_pay, card_payment_wrong_exchange_rate, disposable_card_limits, edit_personal_details, failed_transfer, fiat_currency_support, pending_top_up, receiving_money, request_refund, top_up_reverted.

## Item format
`id` = `banking77-<split>-<row index in CSV, 0-based excluding header>`, `input` = query text, `gold` = intent label,
`meta` = {split, row}.

## Confirmation set (`confirm.jsonl`) — test split
- Purpose: 600 fresh items to confirm findings made on the 200 main items. Built with
  `PYTHONPATH=src python -m gch.build_tasks --confirm` (does not touch `items.jsonl` / `pilot.jsonl`).
- **Seed:** 20261104 (`random.Random(CONFIRM_SEED)`, see `src/gch/build_tasks.py::confirm_banking77`)
- Source rows: test split (`test.csv`, 3,080 rows), same duplicate-text filter as main; additionally excluded every
  text (normalised) appearing in `items.jsonl` or `pilot.jsonl`. Candidate pool after exclusion: 2879 rows.
- Sampling: stratified by intent. Every one of the 77 intents gets 7; 61 distinct intents chosen at random
  get one more (8). Rows sampled uniformly within intent; order shuffled.
- Count: 600. Distribution: 16 intents × 7, 61 intents × 8.
- Disjoint from main and pilot by `id` and by normalised text.

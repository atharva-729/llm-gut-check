# Toxicity task pack (Civil Comments)

- **Source:** Civil Comments (Borkan et al. 2019, arXiv:1903.04561), Hugging Face `google/civil_comments`,
  config `default`, via the datasets-server API (https://datasets-server.huggingface.co/rows).
- **Licence:** CC0 1.0 (HF dataset card `license: cc0-1.0`; the original Civil Comments / Jigsaw
  Unintended Bias release is also CC0).
- **Date fetched:** 2026-11-03
- **Seed:** 20261103 (`random.Random(SEED)`, see `src/gch/build_tasks.py::build_toxicity`)
- **Gold:** `toxicity` (fraction of annotators rating the comment toxic or very toxic) **≥ 0.5 → YES**, else NO.
  Raw score kept in `meta.toxicity`.

## Candidate pool (bounded slice, not the full 2M rows)
- Main: test split rows 0–5999 (of 97,320). Pilot: validation split rows 0–1499 (of 97,320).
- Filters: comment length **20–600 characters** inclusive (Python `len` on the raw text);
  exact duplicate texts (case/whitespace-normalised) dropped within each split.
- After filtering: test pool 419 YES / 4514 NO; validation pool 84 YES / 1166 NO.

## Main (`items.jsonl`) — test split
- Stratified random sample: exactly 60 YES + 140 NO (30% toxic, fixed by design — the natural rate in the
  pool is 8.5%). Order shuffled. Count: 200 (YES 60, NO 140).

## Pilot (`pilot.jsonl`) — validation split
- Exactly 3 YES + 7 NO, excluding any text identical (normalised) to a main item.
  Count: 10 (YES 3, NO 7).

## Item format
`id` = `toxicity-<split>-<HF row_idx>`, `input` = comment text, `gold` = `YES`|`NO`,
`meta` = {split, row_idx, toxicity}.

# Reproduction Package Manifest

Status: `staged` = copied into this package. Hashes are in `MANIFEST.sha256` and
verified by `scripts/verify_hashes.py`. Current release layer: **Layer 1 offline
statistical verification** (see `README_REPRO.md` §1); the frozen engine and
runner for Layer 2 are not shipped.

## Staged files

### Top level
- `README_REPRO.md` — scope, pairing key, offline acceptance, provenance
- `MANIFEST.md` — this list
- `MANIFEST.sha256` — hashes of all staged files (excludes itself)
- `REFERENCE_CHECK.md` — title + DOI reference verification log
- `requirements.txt` — Layer 2 optional environment lock; not needed for Layer 1

### prompts/
- `01_情景抽取_system.txt`, `02_情景抽取_user模板.txt`, `03_智能体决策_system.txt`,
  `04_知识抽取_system.txt`, `05_情景推演_system.txt`, `README.md`

### config/protocol/
- `formal_protocol.json` (v20261019_formal frozen protocol)
- `cache1_protocol.json`, `cache1_manifest.json` (v20261018_cache1 historical, archive only)

### data/knowledge/
- `人群画像分布.json`, `同义词词典.csv`, `情景本体.json`, `知识库.json`,
  `空间与运动参数.json`, `空间与运动参数.xlsx`

### data/clean_main/ (clean three-model main table)
- `clean_main_450.csv` — 25 cids × 6 seeds × 3 models, 450 run rows; paired by (cid, seed)
- `rule/runs.csv` — rule reference 150 runs (audit)
- `clean_reruns/EXP-049_20261059/`, `EXP-088_20261011/`, `EXP-095_20261047/`
  (summary.json + manifest.json); `clean_049.log`, `clean_rest.log` (rerun log index)

### data/ablation_kb/ (#79)
- `t79_paired_detail.csv` — 36 ON/OFF pairs with integer n and outcome counts
- `t79_diagnose_report.md`

### data/sensitivity_t80/ (#80)
- `t80_all.csv` (450 rows = 150 pairs × 3 versions), `base_fine.csv` (300 rows),
  `sensitivity_t80_report.md`, `t80_summary.txt` (pair difference detail)

### scripts/ (offline, standard library only)
- `rebuild_main_table.py` — model set/key/closure/safe checks; pooled anchors;
  run means; paired differences, W/L/T, fixed-seed paired bootstrap and
  cluster-by-cid 95% intervals
- `ablation_summary.py` — 18-pair structural checks; run-level mean and
  population-weighted ON−OFF from integer counts; W/L/T
- `sensitivity_t80.py` — closure, pair-by-pair FINE−BASE/WALK−FINE, pooled anchors
- `verify_hashes.py` — sha256 verification

### docs/
- `DATA_DICTIONARY.md` — field definitions and statistical boundaries

## Excluded
- `.env`, API keys, account credentials;
- `standards/` copyrighted source PDFs;
- `results/cache/`, `results/formal_cache/`, `results/figures/`;
- historical chapter scripts 00–73 under code, `_chk_*`/temporary debug files;
- raw per-event request/response, retry usage detail, unsourced old results;
- frozen engine source and runner (reserved for a possible Layer 2 release).

## Release decisions (confirmed)
- Public repository: `https://github.com/linfeng000lf-tech/underground-flood-evac-repro`;
- Per-event request/response logs are **not** published (aggregated run-level data only);
- This is Layer 1 offline statistical verification; the frozen engine and runner are reserved for a possible later Layer 2 release.

# Release manifest

Release: 2026-10-24. Scope: offline statistical verification and documented
configuration inputs for the manuscript "Knowledge-Informed LLM Agents for Flood
Evacuation in Underground Spaces". This is not an end-to-end engine release.
The public repository's `legacy/` directory is explicitly excluded.

The release includes integer main outcomes, paired retrieval outcomes, rule
sensitivities, process aggregates, exit-time frequencies, actual scenario and
network inputs, and an aggregate WALK endpoint audit. It contains no formal
engine, formal runner, per-event request/response transcript or credentials.

Console files clean_049.log and clean_rest.log are private local audit records.
They are not release dependencies and are not listed in MANIFEST.sha256.

The original planned protocol is retained as an archive. The root formal
protocol is a retrospective record of execution, not a preregistration.

## File list

- `config/protocol/archive/formal_protocol_planned_v20261019.json`
- `config/protocol/cache1_manifest.json`
- `config/protocol/cache1_protocol.json`
- `config/protocol/formal_protocol.json`
- `config/scenarios/main_paired25.json`
- `config/scenarios/station_network.json`
- `data/ablation_kb/knowledge_example.json`
- `data/ablation_kb/knowledge_selection_coverage.csv`
- `data/ablation_kb/process_runs_72.csv`
- `data/ablation_kb/t79_diagnose_report.md`
- `data/ablation_kb/t79_paired_detail.csv`
- `data/clean_main/clean_main_450.csv`
- `data/clean_main/clean_reruns/EXP-049_20261059/manifest.json`
- `data/clean_main/clean_reruns/EXP-049_20261059/summary.json`
- `data/clean_main/clean_reruns/EXP-088_20261011/manifest.json`
- `data/clean_main/clean_reruns/EXP-088_20261011/summary.json`
- `data/clean_main/clean_reruns/EXP-095_20261047/manifest.json`
- `data/clean_main/clean_reruns/EXP-095_20261047/summary.json`
- `data/clean_main/exit_time_histogram.csv`
- `data/clean_main/process_runs_300.csv`
- `data/clean_main/rule/runs.csv`
- `data/knowledge/人群画像分布.json`
- `data/knowledge/同义词词典.csv`
- `data/knowledge/情景本体.json`
- `data/knowledge/知识库.json`
- `data/knowledge/空间与运动参数.json`
- `data/knowledge/空间与运动参数.xlsx`
- `data/sensitivity_t80/base_fine.csv`
- `data/sensitivity_t80/sensitivity_t80_report.md`
- `data/sensitivity_t80/t80_all.csv`
- `data/sensitivity_t80/t80_summary.txt`
- `data/sensitivity_t80/walk_endpoint_audit.csv`
- `data/sensitivity_t80/walk_endpoint_audit.json`
- `docs/DATA_DICTIONARY.md`
- `LICENSE`
- `MANIFEST.md`
- `prompts/01_情景抽取_system.txt`
- `prompts/02_情景抽取_user模板.txt`
- `prompts/03_智能体决策_system.txt`
- `prompts/04_知识抽取_system.txt`
- `prompts/05_情景推演_system.txt`
- `prompts/README.md`
- `README.md`
- `README_REPRO.md`
- `REFERENCE_CHECK.md`
- `requirements.txt`
- `scripts/ablation_summary.py`
- `scripts/rebuild_main_table.py`
- `scripts/rebuild_process_tables.py`
- `scripts/sensitivity_t80.py`
- `scripts/verify_hashes.py`

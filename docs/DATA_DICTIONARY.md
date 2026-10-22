# Data Dictionary

This package publishes run-level aggregated results and paired summaries only;
raw per-event request/response is not included. All counts are integers;
proportions are normalized within a run.

## 1. `data/clean_main/clean_main_450.csv` — Clean three-model main table (450 rows)

25 scenarios (`cid`) × 6 seeds × 3 models (`rule_reference` / `deepseek` /
`qwen`). Runs are matched by **(`cid`, `seed`)**; the three models share the
same six seeds, so the 150 matched groups carry identical `(cid, seed)`.
`repeat_index` (0–5) is a deterministic label for the six seeds, not a pairing
key.

| Column | Meaning |
|---|---|
| cid | Scenario identifier (EXP-xxx), consistent with the frozen protocol |
| seed | Random seed; matching key together with `cid` |
| model | `rule_reference` / `deepseek` / `qwen` |
| repeat_index | Deterministic ordinal label of the six seeds (0–5), auxiliary only |
| n | Headcount of the run |
| evacuated | Self-evacuation or guided walking exit count (includes `guided_exit`) |
| rescued | Agents completing a safe departure via rescue transfer |
| stranded | Terminal stranded agents: agents not completing safe departure and not accounted for by rescue transfer; reachable-but-waiting-capacity agents may also fall here, so this is not limited to "outside the rescue-reachable component" |
| deceased | Fatality-proxy count (model depth-threshold proxy, not an empirical drowning threshold) |
| alive_in | Still on-site at the observation endpoint, safe departure not completed |
| safe | Safe-departure count = evacuated + rescued |

Closure: `n = evacuated + rescued + stranded + deceased + alive_in`.
Population-weighted safe-departure = `Σsafe / Σn` (N = 22,680 per model).
Anchors: rule 0.9086 (deceased 2,073), deepseek 0.9996 (deceased 9),
qwen 0.9757 (deceased 551).

## 2. `data/clean_main/clean_reruns/` — 3 cleaned QW fault-key reruns

Original mixed (API-failure rule fallback) records remain in the local audit
copy and are not published; this folder holds only the successful rerun
`summary.json` / `manifest.json` and an index of logs. Reruns replace on
interface-fault grounds, never on result quality, and the original attempt is
not overwritten.

## 3. `data/ablation_kb/t79_paired_detail.csv` — #79 retrieval ablation (36 rows)

6 cids × 3 seeds × 2 providers; each row is one ON/OFF pair. ON ran before OFF
(fixed runner order, not randomized interleaving); this is a targeted,
exploratory ablation.

| Column | Meaning |
|---|---|
| provider | `deepseek` / `qwen` |
| cid, seed | Scenario and repeated seed; the pairing key |
| on_safe / off_safe | Safe-departure proportion (ON retrieval on / OFF retrieval off) |
| on_death / off_death | Fatality-proxy proportion |
| on_stranded / off_stranded | Stranded proportion |
| on_in / off_in | On-site-at-endpoint proportion |
| on_wait / off_wait | Share of wait-type events among successful decision events (event frequency, not time share) |
| on_takeover / off_takeover | **API-failure fallback proportion = fallback_events / calls**; this is the share of calls that fell back after an API failure, **not** a rule-takeover rate and not a measure of ongoing rule adjudication |
| on_mixed / off_mixed | `True` when the run had any fallback event; clean pairs require both ends `False` |
| on_calls / off_calls | LLM call count |
| on_fb / off_fb | **API-failure fallback event count (integer)**, not a proportion |
| on_model / off_model | Returned model identifier (deepseek-flash / qwen-plus) |
| n | Headcount, identical on ON and OFF within a pair |
| on_safe_n / off_safe_n | Integer safe-departure count (= evacuated + rescued) |
| on_evac_n / off_evac_n | Integer self/guided exit count |
| on_rescued_n / off_rescued_n | Integer rescue-transfer count |
| on_death_n / off_death_n | Integer fatality-proxy count |
| on_stranded_n / off_stranded_n | Integer stranded count |
| on_in_n / off_in_n | Integer on-site-at-endpoint count |

Population-weighted ON−OFF is recomputed from these integer counts; individual
logs are not required for it.

## 4. `data/sensitivity_t80/t80_all.csv` — #80 rule-layer sensitivity (450 rows)

150 matched runs × 3 versions (BASE / FINE / WALK), paired by `(cid, seed)`.

| Column | Meaning |
|---|---|
| version | BASE instantaneous transfer + original check interval; FINE fine check interval; WALK actual walking + 10 s check |
| n, evacuated, rescued, deceased, in | Outcome counts; `in` = on-site at window end (WALK 488), not counted safe |
| safe | Safe departure = evacuated + rescued; reachable-but-not-exited at window end is not counted |
| guided_exit / self_evac | Guided walking exit / self-evacuation split |
| potential_reachable | Separate "currently reachable safe exit" indicator, not equivalent to having left |

Comparison chain: FINE−BASE = check interval; WALK−FINE = transfer mode;
WALK−BASE = combined control of both changes (not a single-variable ablation).
Pair-by-pair: FINE−BASE safe/death/in are equal on all 150 pairs; WALK−FINE
keeps the death count equal on every pair while safe and in differ on 32 pairs.

## 5. Protocol and prompts

- `config/protocol/formal_protocol.json`: v20261019_formal frozen protocol
  (scenarios, capacity, endpoint, repeats, fault rules).
- `prompts/`: decision and extraction prompt text.
- `data/knowledge/`: crowd-profile distribution, synonym dictionary, scenario
  ontology, knowledge base, spatial/motion parameters.

## Scope cautions

- Population-weighted proportion and run-mean paired difference are different
  statistics and are not interchangeable.
- An undetected difference is not proof of no effect or equivalence; this is a
  limited sample and does not support broad generalization.
- This package excludes raw per-event logs, API request/response, retry-usage
  detail, and keys.

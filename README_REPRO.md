# Reproduction package

This release accompanies **Knowledge-Informed LLM Agents for Flood Evacuation in Underground Spaces**.
Public repository: https://github.com/linfeng000lf-tech/underground-flood-evac-repro

## Release scope

This is an offline statistical verification package. It supports Tables 5 and 6
(main outcomes and paired comparisons), Table 7 (retrieval outcomes and process
summaries), Table 8 (rule sensitivities), and the process statistics in Section 4.2.
It also documents the actual 25 scenario configurations, the implemented station
network and the endpoint audit. It does not reproduce a simulation from scratch.

The formal experimental engine, its runners and raw per-event requests and
responses are not part of this release. No API key is needed for the verification
scripts. The repository's separate `legacy/` directory contains earlier
exploratory code and inputs. Those assets are not the formal experimental engine
and must not be substituted for it. The root release manifest excludes `legacy/`.

## Offline verification

Use Python 3.10 or newer from the package root. Only the standard library is used.
No network, provider account, API request or paid service is involved.

```powershell
python scripts/rebuild_main_table.py
python scripts/ablation_summary.py
python scripts/sensitivity_t80.py
python scripts/rebuild_process_tables.py
python scripts/verify_hashes.py
```

Each script prints `RESULT: PASS` and exits zero on success. A structural,
matching, closure, numerical anchor or hash failure exits nonzero.
`requirements.txt` describes the optional simulation environment. It is not
needed for these statistical checks and does not supply the missing formal engine.

## Experiments and pairing

Runs are matched by `(cid, seed)`, never by row order. `repeat_index` is only a
deterministic label of the six simulation seeds. The main experiment has 25
scenarios, six seeds and three decision models, giving 450 runs. Each model has
22,680 simulated agent instances. The simulation seed controls profiles and
placement. It is not a remote sampling seed and does not establish independence
of language model outputs.

`config/scenarios/main_paired25.json` contains the actual `cid` to configuration
mapping. `config/scenarios/station_network.json` describes the ten-node,
two-exit network. `config/protocol/formal_protocol.json` records the executed
methods retrospectively. It is not a preregistration. The original planned
protocol is retained under `config/protocol/archive/`. The historical cache
protocol and manifest are labeled archives rather than execution records.

The endpoint is rescue arrival plus 120 minutes, with earlier stopping when all
agents are evacuated, rescued or deceased. Configured main endpoints are 140,
155 and 170 minutes. The implementation updates a 10-second grid below the
configured endpoint. A no-rescue configuration would use 150 minutes. Minute 5
marks the end of initial seepage at the inlet, not the first appearance of water.

## Main outcome and process data

- `data/clean_main/clean_main_450.csv`: integer headcounts and all five outcomes.
- `data/clean_main/rule/runs.csv`: original rule result audit copy.
- `data/clean_main/clean_reruns/`: completed Qwen replacement summaries and manifests.
- `data/clean_main/process_runs_300.csv`: aggregate first-decision and early-exit
  counts for the 150 DeepSeek and 150 Qwen runs.
- `data/clean_main/exit_time_histogram.csv`: pooled exit-time frequencies from
  saved successful-exit times. These are not individual trajectories.

The three Qwen fault keys are EXP-049/20261059, EXP-088/20261011 and
EXP-095/20261047. The replacements are completed runs with no heuristic fallback.
Selection is based on execution validity rather than evacuation outcome. Original
mixed attempts remain in the private local audit record. Rerun console logs are
not included in this release or its hash manifest.

Population-weighted safe departure is 20,607/22,680 for the rule model,
22,671/22,680 for DeepSeek and 22,129/22,680 for Qwen. Fatalities are 2,073,
9 and 551. Run means and paired differences are different estimands from pooled
proportions. Paired and whole-scenario cluster bootstrap intervals use 10,000
replicates and seed 20261022, with sorted traversal of keys and scenario groups.

Initial evacuation-action shares are 71.8% and 23.2%. They are selections, not
completed departures. Among successful autonomous exiters, 78.0% and 28.2% leave
before simulation minute 5. Their pooled median exit times are 2.17 and 9.83 min.
Rule exit-time logs are not provided and no matched LLM-minus-rule timing claim
is supported by these summaries.

## Retrieval ablation

The targeted experiment includes six scenarios, three seeds, two providers and
ON/OFF conditions, giving 72 completed runs and 36 pairs. Each provider and
condition contains 18 runs and 3,180 agent instances. ON precedes OFF within each
block. This order was not randomized. OFF empties only the retrieved list.

- `t79_paired_detail.csv` publishes integer outcomes for each pair.
- `process_runs_72.csv` publishes successful event counts, waiting events,
  non-null target counts and within-run exit-time medians.
- `knowledge_selection_coverage.csv` reconstructs selected item counts from saved
  tags and the unchanged deterministic retrieval rule. It does not claim to
  contain retained raw requests.
- `knowledge_example.json` documents the example in Table 2.
- `t79_diagnose_report.md` explains statistical scope.

Process proportions are calculated per run and averaged over runs. Waiting-event
frequency is not elapsed waiting time. Non-null targets are not correctness or
movement measures. Exit-time medians include successful autonomous exiters only.
Fourteen of 23 items are selected in ON contexts. K08 and K09 are not selected in
this batch. An undetected difference is not proof of no effect or equivalence.

## Rule sensitivities and endpoint audit

Each of BASE, FINE and WALK uses 150 matched rule runs. BASE and FINE have 20,607
safe departures and 2,073 fatalities. WALK has 20,119 safe departures, 2,073
fatalities and 488 active agents still inside.

FINE minus BASE varies assessment frequency. WALK uses explicit guided walking
on the FINE clock and has additional endpoint checks. Its endpoint finalizer
assesses unreachable active agents using depth or the fatality timer. It also
checks the timer for stranded agents. FINE checks stranded agents against current
depth only at finalization. These rules differ in general.

`walk_endpoint_audit.csv` records all 150 WALK runs. The additional endpoint
branches trigger zero state changes. Applying both finalizers to the same
pre-finalization WALK states yields zero individual state differences. The audit
also reproduces the published final counts. This is not a comparison of individual
trajectories across FINE and WALK and does not establish general equivalence.

## Boundaries and provenance

The package excludes keys, credentials, copyrighted source documents, historical
response caches and raw request/response logs. Synthetic agent identifiers in the
knowledge example do not identify real people. Requested and returned model names
are recorded service identifiers, not locked weight snapshots.

Formal run outcomes, process aggregates and ablation summaries were rebuilt from
locally retained records. The endpoint audit reruns unchanged WALK rules offline.
Published final outcome values are unchanged. Hashes cover the release files,
excluding the hash manifest itself. The public `legacy/` tree is outside this
manifest and outside the formal evidence claim.

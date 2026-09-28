# Cognitive LLM Agents for Crowd Evacuation in Underground Flooding

Reproducibility package for the study that uses large-language-model (LLM) cognitive
agents to mine individual evacuation behaviour patterns during flooding in urban
underground space (metro stations and connected underground networks).

The package provides the simulation engine, the perception-appraisal-coping cognitive
agent, the scenario library and controlled vocabularies, the experiment design, and the
aggregated outputs underlying the manuscript's tables and figures. API keys are never
included; you must supply your own keys in a local `.env` file.

## Repository structure

- `code/` - simulation, cognitive agent, experiment design, validation, association
  rules, machine-learning models, SHAP analysis, real-LLM replication, adverse scenarios.
- `prompts/` - system and user prompt templates used for scenario extraction and for
  agent decision-making.
- `data/knowledge/` - flood scenario ontology, knowledge base, population profiles,
  space and movement parameters.
- `data/processed/` - cleaned source datasets, controlled vocabulary, parameterised
  scenario library, four-stage water-depth templates, data dictionary.
- `results/runs/` - aggregated run-level and individual-level outputs (including the
  281,600 labelled individual records), real-LLM replication tables, association rules,
  ML metrics, SHAP values and the adverse-scenario family.
- `docs/` - reproduction guide, data dictionary, validity and cross-model reports, and
  notes on the scientific basis of the parameters.

## Environment

- Python 3.10; install dependencies with `pip install -r requirements.txt`.
- Create a `.env` file (see `code/llm_utils.py`) with your LLM API credentials.
- The heuristic and analysis pipelines run offline; real-LLM runs require API access.

## Reproduction

1. Scenario library: run `code/09` through `code/16` (ontology, extraction, controlled
   vocabulary, depth parameterisation, scenario library).
2. Cognitive model and validation: `code/24` to `code/38` (knowledge base, agent,
   engine, case replay, classic effects, holdout, experiment design, batch runs).
3. Behaviour mining: `code/41` to `code/48` (features, descriptive statistics,
   association rules, ML models, SHAP, cross-validation, intervention thresholds).
4. Real-LLM replication and adverse scenarios: `code/50`, `code/55` to `code/57`.

A Windows entry point is provided in `一键复现.bat`.

## Notes on scope

The model reproduces directional effects and non-fatal evacuation timing. Flood-fatality
ratios are conditional outputs for open-network deep-water entrapment under stated
assumptions; the confined-train overtopping mechanism of specific real incidents is not
modelled. See the manuscript and `docs/` for the validity framework and the boundary
conditions under which a zero-fatality outcome holds.

## License

Code is released under the MIT License (see `LICENSE`). Datasets in `data/` and
`results/` are made available for academic reproduction of this study.

## Citation

[Citation details and DOI to be added upon publication.]

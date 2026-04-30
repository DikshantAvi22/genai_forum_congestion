# Selective Response for GenAI Under Forum Congestion

This repository contains a deterministic simulator and experiment runner for the forum congestion dynamics project.

## Setup

```bash
cd /home/dikshantg/genai_forum_congestion
python3 -m venv .venv
source .venv/bin/activate
pip install -r sim/requirements.txt
```

## Run Experiments

```bash
python sim/run_experiments.py --mode quick
```

For larger sweeps and more seed repetitions:

```bash
python sim/run_experiments.py --mode full
```

## Outputs

- Figures are saved to `sim/figs/`
- Tables and summaries are saved to `sim/results/`
- Additional follow-up figures are saved to `sim/figs/extra/`
- Additional follow-up tables and notes are saved to `sim/results/extra/`

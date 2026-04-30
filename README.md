# Selective Response for GenAI Under Forum Congestion

This repository contains the manuscript, simulator, and generated experiment artifacts for a reduced-form study of selective response policies for GenAI systems when the human fallback channel is a congestible forum.

The central question is simple: when should a GenAI system answer directly, and when should it defer traffic to a human forum whose capacity can degrade under overload? The project studies how response policy affects long-run learning, forum health, welfare, and platform-side incentives.

## Main Result

Within the simulator studied here, novelty-aware routing consistently outperforms uniform throttling in long-run learning. The advantage survives a matched answered-share control and disappears when novelty is removed from the knowledge-gain mechanism, which supports the intended composition-based explanation rather than a pure volume effect.

## Repository Layout

```text
paper/          Manuscript source, bibliography, and compiled PDF
sim/            Deterministic simulator, policies, figures, and result tables
presentation/   Slide decks and presentation assets
make_*.py       Scripts used to generate presentation variants
```

Canonical paper artifacts:

- Manuscript source: `paper/main.tex`
- Compiled manuscript: `paper/main.pdf`
- Build notes: `paper/README_build.txt`

Canonical simulation artifacts:

- Experiment runner: `sim/run_experiments.py`
- Core simulator: `sim/model.py`
- Policies: `sim/policies.py`
- Main summaries: `sim/results/summary.md`, `sim/results/extra/summary_extra.md`

## Setup

```bash
cd /home/dikshantg/genai_forum_congestion
python3 -m venv .venv
source .venv/bin/activate
pip install -r sim/requirements.txt
```

## Reproducing Experiments

Quick run:

```bash
python sim/run_experiments.py --mode quick
```

Larger sweep:

```bash
python sim/run_experiments.py --mode full
```

Generated outputs are written to:

- `sim/figs/` for baseline figures
- `sim/figs/extra/` for robustness and follow-up figures
- `sim/results/` for baseline tables and summaries
- `sim/results/extra/` for extended comparisons, ablations, and robustness tables

## Building the Paper

```bash
cd paper
latexmk -pdf main.tex
```

The manuscript directly includes figures from `../sim/figs/` and `../sim/figs/extra/`.

## Project Scope

This is a reduced-form research simulator, not a platform-accurate deployment model. The code is designed to make the selective-response mechanism, congestion channel, and policy comparisons easy to inspect and reproduce.

The repository includes:

- stable, mid, and collapse regime comparisons
- seed robustness checks
- novelty-distribution robustness
- novelty-weight ablations
- matched answered-share controls
- collapse-boundary and phase-diagram sweeps
- extended comparisons against congestion-aware baselines

## Authors

- Dikshant Gupta
- Paras Raina

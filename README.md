# Selective Response for GenAI Under Forum Congestion

This repository contains the core simulator code for a reduced-form study of selective response policies for GenAI systems when the human fallback channel is a congestible forum.

The project studies a simple question: when should a GenAI system answer directly, and when should it defer traffic to a human forum whose capacity can degrade under overload?

## Repository Layout

```text
sim/            Core simulator, policy definitions, and experiment runner
README.md       Project overview
```

Key code files:

- `sim/run_experiments.py`
- `sim/model.py`
- `sim/policies.py`
- `sim/models/reduced_form.py`

## Setup

```bash
cd /home/dikshantg/genai_forum_congestion
python3 -m venv .venv
source .venv/bin/activate
pip install -r sim/requirements.txt
```

## Running

```bash
python sim/run_experiments.py --mode quick
```

For the larger sweep:

```bash
python sim/run_experiments.py --mode full
```

## Scope

This is a compact research code repository. It keeps the simulator and policy logic, while large manuscript, presentation, and generated artifact directories have been removed from version control.

## Authors

- Dikshant Gupta
- Paras Raina

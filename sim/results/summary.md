# Experiment Summary

The simulator is deterministic with a fixed novelty seed and horizon `T=40`.

## Findings

- Non-monotonicity was observed qualitatively in the `C_1` vs `xi` sweep: lower initial capacity and higher overload penalty sharply reduce final learning and forum health after a threshold.
- Collapse occurs in the collapse run: capacity decays toward zero and overload persists for most rounds.
- At matched answer rate `x_target=0.60`, targeted novelty deferral changes who reaches the forum. In this setup it changes `S_T` by `11.989` and `overload_time` by `-15.000` relative to uniform throttling.

## Parameter Configurations

- Stable regime: `{'horizon': 40, 's0': 0.0, 'c0': 0.85, 'alpha': 0.12, 'beta': 8.0, 'w_s': 0.55, 'kappa': 1.0, 'overflow_discount': 0.2, 'delta': 0.03, 'eta': 0.05, 'xi': 0.04, 'response_effort': 1.0, 'novelty_weight': 0.35, 'novelty_rho': 1.0, 'revenue_gamma': 0.95}`
- Collapse regime: `{'horizon': 40, 's0': 0.0, 'c0': 0.35, 'alpha': 0.12, 'beta': 8.0, 'w_s': 0.55, 'kappa': 1.0, 'overflow_discount': 0.2, 'delta': 0.03, 'eta': 0.05, 'xi': 0.35, 'response_effort': 1.0, 'novelty_weight': 0.35, 'novelty_rho': 1.0, 'revenue_gamma': 0.95}`
- Policy comparison base regime: `{'horizon': 40, 's0': 0.0, 'c0': 0.6, 'alpha': 0.12, 'beta': 8.0, 'w_s': 0.55, 'kappa': 1.0, 'overflow_discount': 0.2, 'delta': 0.03, 'eta': 0.05, 'xi': 0.1, 'response_effort': 1.0, 'novelty_weight': 0.35, 'novelty_rho': 1.0, 'revenue_gamma': 0.95}`
- Sweep axes:
  - `C_1`: 0.25 to 1.05 with 9 points
  - `xi`: 0.02 to 0.38 with 9 points

## Policy Metrics

| Policy | S_T | minC | overload_time | avg_choice | avg_answered | W | U |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| uniform | 19.602 | 0.476 | 40.000 | 0.246 | 0.148 | 23.254 | 0.285 |
| targeted_match_rate | 31.592 | 0.541 | 25.000 | 0.347 | 0.208 | 24.628 | 0.580 |

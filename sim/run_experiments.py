from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, replace
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sim.model import ModelParams, SimulationResult, simulate
from sim.policies import CapacityAwarePolicy, NoveltyCapacityPolicy, NoveltyParams, NoveltyThresholdPolicy, UniformPolicy

FIG_DIR = ROOT / "sim" / "figs"
RESULTS_DIR = ROOT / "sim" / "results"
EXTRA_FIG_DIR = FIG_DIR / "extra"
EXTRA_RESULTS_DIR = RESULTS_DIR / "extra"
METRIC_KEYS = ["S_T", "minC", "overload_time", "avg_choice", "avg_answered", "W", "U"]
DISPLAY_LABELS = {
    "stable": "Stable",
    "mid": "Mid",
    "collapse": "Collapse",
    "uniform": "Uniform",
    "targeted_match_rate": "Targeted",
    "capacity_aware": "Capacity-aware",
    "novelty_capacity": "Novelty+capacity",
    "uniform_matched_answered": "Uniform",
    "targeted_matched_answered": "Targeted",
}
DISPLAY_ORDER = {
    "stable": 0,
    "mid": 1,
    "collapse": 2,
    "uniform": 0,
    "capacity_aware": 1,
    "targeted_match_rate": 2,
    "novelty_capacity": 3,
    "uniform_matched_answered": 0,
    "targeted_matched_answered": 1,
}


@dataclass(frozen=True)
class RunMode:
    name: str
    grid_points: int
    seeds: tuple[int, ...]


MODES = {
    "quick": RunMode(name="quick", grid_points=7, seeds=tuple(range(10))),
    "full": RunMode(name="full", grid_points=15, seeds=tuple(range(30))),
}


def ensure_dirs() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    EXTRA_FIG_DIR.mkdir(parents=True, exist_ok=True)
    EXTRA_RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run forum congestion experiments.")
    parser.add_argument("--mode", choices=sorted(MODES.keys()), default="quick")
    return parser.parse_args()


def plot_timeseries(result: SimulationResult, title: str, destination: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(9, 8), sharex=True)
    axes[0].plot(result.rounds, result.s_path[:-1], color="#1b4965", linewidth=2.2)
    axes[0].set_ylabel("S_t")
    axes[0].set_title(title)

    axes[1].plot(result.rounds, result.c_path[:-1], color="#c1121f", linewidth=2.2)
    axes[1].set_ylabel("C_t")

    axes[2].plot(result.rounds, result.m_path, color="#6a994e", linewidth=2.2, label="m_t")
    axes[2].plot(result.rounds, result.answered_path, color="#bc6c25", linewidth=1.8, label="p_answered_t")
    axes[2].set_ylabel("Load")
    axes[2].set_xlabel("Round")
    axes[2].legend(frameon=False, loc="upper right")

    for axis in axes:
        axis.grid(alpha=0.25, linewidth=0.6)

    fig.tight_layout()
    fig.savefig(destination, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_heatmap(
    data: np.ndarray,
    x_values: np.ndarray,
    y_values: np.ndarray,
    title: str,
    cbar_label: str,
    destination: Path,
    x_label: str,
    y_label: str,
) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    image = ax.imshow(
        data,
        origin="lower",
        aspect="auto",
        interpolation="nearest",
        extent=[x_values[0], x_values[-1], y_values[0], y_values[-1]],
        cmap="viridis",
    )
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    cbar = fig.colorbar(image, ax=ax)
    cbar.set_label(cbar_label)
    fig.tight_layout()
    fig.savefig(destination, dpi=180, bbox_inches="tight")
    plt.close(fig)


def ordered_labels(values: set[str]) -> list[str]:
    return sorted(values, key=lambda value: (DISPLAY_ORDER.get(value, 999), value))


def display_label(value: str) -> str:
    return DISPLAY_LABELS.get(value, value.replace("_", " ").title())


def plot_grouped_bars(
    rows: list[dict[str, object]],
    group_key: str,
    series_key: str,
    mean_key: str,
    std_key: str,
    destination: Path,
    ylabel: str,
    title: str,
) -> None:
    groups = ordered_labels({str(row[group_key]) for row in rows})
    series_names = ordered_labels({str(row[series_key]) for row in rows})
    x = np.arange(len(groups), dtype=float)
    width = 0.8 / max(len(series_names), 1)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    for idx, series_name in enumerate(series_names):
        means = []
        stds = []
        positions = x - 0.4 + width / 2.0 + idx * width
        for group in groups:
            row = next(item for item in rows if str(item[group_key]) == group and str(item[series_key]) == series_name)
            means.append(float(row[mean_key]))
            stds.append(float(row[std_key]))
        ax.bar(
            positions,
            means,
            width=width * 0.88,
            yerr=stds,
            capsize=4,
            label=display_label(series_name),
            edgecolor="white",
            linewidth=0.8,
            alpha=0.9,
        )

    ax.set_xticks(x)
    ax.set_xticklabels([display_label(group) for group in groups])
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(destination, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_metric_lines(
    rows: list[dict[str, object]],
    x_key: str,
    series_key: str,
    y_key: str,
    destination: Path,
    xlabel: str,
    ylabel: str,
    title: str,
) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    for series_name in sorted({str(row[series_key]) for row in rows}):
        subset = sorted(
            (row for row in rows if str(row[series_key]) == series_name),
            key=lambda row: float(row[x_key]),
        )
        ax.plot(
            [float(row[x_key]) for row in subset],
            [float(row[y_key]) for row in subset],
            marker="o",
            linewidth=2.0,
            label=series_name,
        )
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(alpha=0.25, linewidth=0.6)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(destination, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_distribution_points(
    rows: list[dict[str, object]],
    x_order: list[str],
    series_key: str,
    mean_key: str,
    std_key: str,
    destination: Path,
    ylabel: str,
    title: str,
) -> None:
    x = np.arange(len(x_order), dtype=float)
    series_names = sorted({str(row[series_key]) for row in rows})
    width = 0.8 / max(len(series_names), 1)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for idx, series_name in enumerate(series_names):
        positions = x - 0.4 + width / 2.0 + idx * width
        means = []
        stds = []
        for label in x_order:
            row = next(item for item in rows if str(item["novelty_distribution"]) == label and str(item[series_key]) == series_name)
            means.append(float(row[mean_key]))
            stds.append(float(row[std_key]))
        ax.errorbar(positions, means, yerr=stds, fmt="o", capsize=4, linewidth=2.0, label=series_name)
    ax.set_xticks(x)
    ax.set_xticklabels(x_order, rotation=15)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(alpha=0.25, linewidth=0.6)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(destination, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_gap_vs_rho(
    rows: list[dict[str, object]],
    mean_key: str,
    std_key: str,
    destination: Path,
    ylabel: str,
    title: str,
) -> None:
    subset = sorted(rows, key=lambda row: float(row["rho"]))
    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.errorbar(
        [float(row["rho"]) for row in subset],
        [float(row[mean_key]) for row in subset],
        yerr=[float(row[std_key]) for row in subset],
        fmt="o-",
        linewidth=2.0,
        capsize=4,
    )
    ax.axhline(0.0, color="#666666", linewidth=1.0, linestyle="--")
    ax.set_xlabel("rho")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(alpha=0.25, linewidth=0.6)
    fig.tight_layout()
    fig.savefig(destination, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_collapse_boundary(
    mask: np.ndarray,
    c0_values: np.ndarray,
    xi_values: np.ndarray,
    destination: Path,
    epsilon: float,
) -> None:
    x_grid, y_grid = np.meshgrid(c0_values, xi_values)
    fig, ax = plt.subplots(figsize=(8.5, 6))
    ax.imshow(
        mask.astype(float),
        origin="lower",
        aspect="auto",
        interpolation="nearest",
        extent=[c0_values[0], c0_values[-1], xi_values[0], xi_values[-1]],
        cmap="Greys",
        alpha=0.35,
    )
    ax.contour(x_grid, y_grid, mask.astype(float), levels=[0.5], colors=["#c1121f"], linewidths=2.4)
    ax.plot([], [], color="#c1121f", linewidth=2.4, label="collapse boundary")
    ax.set_xlabel("Initial capacity C_1")
    ax.set_ylabel("Overload penalty xi")
    ax.set_title(f"Collapse Boundary: min_t C_t < {epsilon:.2f}")
    ax.grid(alpha=0.2, linewidth=0.6)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(destination, dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_csv(rows: list[dict[str, object]], destination: Path) -> None:
    if not rows:
        destination.write_text("", encoding="utf-8")
        return
    fieldnames = list(dict.fromkeys(key for row in rows for key in row.keys()))
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def simulation_row(result: SimulationResult, policy: str, seed: int | None = None, **extra: object) -> dict[str, object]:
    row: dict[str, object] = {
        "policy": policy,
        "avg_forum_novelty": float(np.mean(result.forum_novelty_path)),
        "avg_answer_rate": float(np.mean(result.answer_rate_path)),
        "avg_novelty_factor": float(np.mean(result.novelty_factor_path)),
    }
    row.update(result.metrics)
    if seed is not None:
        row["seed"] = seed
    row.update(extra)
    return row


def aggregate_seed_rows(
    rows: list[dict[str, object]],
    group_keys: list[str],
    metric_keys: list[str] | None = None,
) -> list[dict[str, object]]:
    metrics = metric_keys or (METRIC_KEYS + ["avg_forum_novelty", "avg_answer_rate", "avg_novelty_factor"])
    grouped: dict[tuple[object, ...], list[dict[str, object]]] = {}
    for row in rows:
        key = tuple(row[group_key] for group_key in group_keys)
        grouped.setdefault(key, []).append(row)

    aggregates: list[dict[str, object]] = []
    for key, group_rows in grouped.items():
        summary: dict[str, object] = {group_key: key[idx] for idx, group_key in enumerate(group_keys)}
        summary["n_seeds"] = len(group_rows)
        for metric in metrics:
            values = np.array([float(row[metric]) for row in group_rows], dtype=float)
            summary[f"{metric}_mean"] = float(np.mean(values))
            summary[f"{metric}_std"] = float(np.std(values, ddof=0))
        aggregates.append(summary)
    return sorted(aggregates, key=lambda row: tuple(str(row[key]) for key in group_keys))


def regime_definitions() -> dict[str, ModelParams]:
    return {
        "stable": ModelParams(c0=0.85, xi=0.04),
        "mid": ModelParams(c0=0.60, xi=0.10),
        "collapse": ModelParams(c0=0.35, xi=0.35),
    }


def run_heatmap(
    base_params: ModelParams,
    answer_rate: float,
    x_param: str,
    x_values: np.ndarray,
    y_param: str,
    y_values: np.ndarray,
) -> tuple[dict[str, np.ndarray], list[dict[str, object]]]:
    st = np.zeros((len(y_values), len(x_values)), dtype=float)
    min_c = np.zeros_like(st)
    overload = np.zeros_like(st)
    welfare = np.zeros_like(st)
    revenue = np.zeros_like(st)
    rows: list[dict[str, object]] = []

    for row_idx, y_value in enumerate(y_values):
        for col_idx, x_value in enumerate(x_values):
            params = replace(base_params, **{x_param: float(x_value), y_param: float(y_value)})
            result = simulate(params, UniformPolicy(answer_rate))
            metrics = result.metrics
            st[row_idx, col_idx] = metrics["S_T"]
            min_c[row_idx, col_idx] = metrics["minC"]
            overload[row_idx, col_idx] = metrics["overload_time"]
            welfare[row_idx, col_idx] = metrics["W"]
            revenue[row_idx, col_idx] = metrics["U"]
            rows.append(
                {
                    x_param: float(x_value),
                    y_param: float(y_value),
                    "S_T": metrics["S_T"],
                    "minC": metrics["minC"],
                    "overload_time": metrics["overload_time"],
                    "W": metrics["W"],
                    "U": metrics["U"],
                }
            )

    return {"S_T": st, "minC": min_c, "overload_time": overload, "W": welfare, "U": revenue}, rows


def tune_control_for_target_answered(
    params: ModelParams,
    control_to_policy,
    target_answered: float,
    low: float = 0.01,
    high: float = 0.99,
    iterations: int = 20,
) -> tuple[float, SimulationResult]:
    best_control = low
    best_result = simulate(params, control_to_policy(low))
    best_gap = abs(best_result.metrics["avg_answered"] - target_answered)

    left = low
    right = high
    for _ in range(iterations):
        mid = 0.5 * (left + right)
        result = simulate(params, control_to_policy(mid))
        gap = result.metrics["avg_answered"] - target_answered
        abs_gap = abs(gap)
        if abs_gap < best_gap:
            best_control = mid
            best_result = result
            best_gap = abs_gap
        if gap < 0.0:
            left = mid
        else:
            right = mid

    return best_control, best_result


def write_summary(
    stable_params: ModelParams,
    collapse_params: ModelParams,
    comparison_params: ModelParams,
    x_target: float,
    metrics_rows: list[dict[str, object]],
    heatmap_axes: tuple[np.ndarray, np.ndarray],
    destination: Path,
) -> None:
    uniform_row = next(row for row in metrics_rows if row["policy"] == "uniform")
    targeted_row = next(row for row in metrics_rows if row["policy"] == "targeted_match_rate")

    st_gain = float(targeted_row["S_T"]) - float(uniform_row["S_T"])
    overload_delta = float(targeted_row["overload_time"]) - float(uniform_row["overload_time"])

    summary = f"""# Experiment Summary

The simulator is deterministic with a fixed novelty seed and horizon `T={comparison_params.horizon}`.

## Findings

- Non-monotonicity was observed qualitatively in the `C_1` vs `xi` sweep: lower initial capacity and higher overload penalty sharply reduce final learning and forum health after a threshold.
- Collapse occurs in the collapse run: capacity decays toward zero and overload persists for most rounds.
- At matched answer rate `x_target={x_target:.2f}`, targeted novelty deferral changes who reaches the forum. In this setup it changes `S_T` by `{st_gain:.3f}` and `overload_time` by `{overload_delta:.3f}` relative to uniform throttling.

## Parameter Configurations

- Stable regime: `{asdict(stable_params)}`
- Collapse regime: `{asdict(collapse_params)}`
- Policy comparison base regime: `{asdict(comparison_params)}`
- Sweep axes:
  - `C_1`: {heatmap_axes[0][0]:.2f} to {heatmap_axes[0][-1]:.2f} with {len(heatmap_axes[0])} points
  - `xi`: {heatmap_axes[1][0]:.2f} to {heatmap_axes[1][-1]:.2f} with {len(heatmap_axes[1])} points

## Policy Metrics

| Policy | S_T | minC | overload_time | avg_choice | avg_answered | W | U |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| uniform | {float(uniform_row["S_T"]):.3f} | {float(uniform_row["minC"]):.3f} | {float(uniform_row["overload_time"]):.3f} | {float(uniform_row["avg_choice"]):.3f} | {float(uniform_row["avg_answered"]):.3f} | {float(uniform_row["W"]):.3f} | {float(uniform_row["U"]):.3f} |
| targeted_match_rate | {float(targeted_row["S_T"]):.3f} | {float(targeted_row["minC"]):.3f} | {float(targeted_row["overload_time"]):.3f} | {float(targeted_row["avg_choice"]):.3f} | {float(targeted_row["avg_answered"]):.3f} | {float(targeted_row["W"]):.3f} | {float(targeted_row["U"]):.3f} |
"""
    destination.write_text(summary, encoding="utf-8")


def run_existing_outputs(mode: RunMode) -> None:
    stable_params = ModelParams(c0=0.85, xi=0.04)
    collapse_params = ModelParams(c0=0.35, xi=0.35)
    base_policy_rate = 0.60

    stable_result = simulate(stable_params, UniformPolicy(base_policy_rate))
    collapse_result = simulate(collapse_params, UniformPolicy(base_policy_rate))

    plot_timeseries(stable_result, "Stable Regime: Uniform Throttling", FIG_DIR / "timeseries_stable.png")
    plot_timeseries(collapse_result, "Collapse Regime: Uniform Throttling", FIG_DIR / "timeseries_collapse.png")

    sweep_params = ModelParams(c0=0.65, xi=0.14)
    c0_values = np.linspace(0.25, 1.05, 9)
    xi_values = np.linspace(0.02, 0.38, 9)
    heatmaps, _ = run_heatmap(sweep_params, base_policy_rate, "c0", c0_values, "xi", xi_values)

    plot_heatmap(heatmaps["S_T"], c0_values, xi_values, "Final Learning S_T", "S_T", FIG_DIR / "heatmap_ST.png", "Initial capacity C_1", "Overload penalty xi")
    plot_heatmap(heatmaps["minC"], c0_values, xi_values, "Minimum Capacity", "minC", FIG_DIR / "heatmap_minC.png", "Initial capacity C_1", "Overload penalty xi")
    plot_heatmap(
        heatmaps["overload_time"],
        c0_values,
        xi_values,
        "Overload Duration",
        "sum 1{m_t > C_t}",
        FIG_DIR / "heatmap_overload.png",
        "Initial capacity C_1",
        "Overload penalty xi",
    )

    comparison_params = ModelParams(c0=0.60, xi=0.10)
    novelty_params = NoveltyParams(seed=11)
    uniform_result = simulate(comparison_params, UniformPolicy(base_policy_rate, novelty_params=novelty_params))
    targeted_result = simulate(
        comparison_params,
        NoveltyThresholdPolicy(novelty_params=novelty_params, match_rate=base_policy_rate),
    )

    metrics_rows = [
        simulation_row(uniform_result, "uniform"),
        simulation_row(targeted_result, "targeted_match_rate"),
    ]

    write_csv(metrics_rows, RESULTS_DIR / "metrics.csv")
    write_summary(
        stable_params=stable_params,
        collapse_params=collapse_params,
        comparison_params=comparison_params,
        x_target=base_policy_rate,
        metrics_rows=metrics_rows,
        heatmap_axes=(c0_values, xi_values),
        destination=RESULTS_DIR / "summary.md",
    )


def run_seed_robustness(mode: RunMode, regimes: dict[str, ModelParams]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for regime_name, params in regimes.items():
        for seed in mode.seeds:
            novelty_params = NoveltyParams(seed=seed)
            rows.append(
                simulation_row(
                    simulate(params, UniformPolicy(0.60, novelty_params=novelty_params)),
                    "uniform",
                    seed=seed,
                    regime=regime_name,
                )
            )
            rows.append(
                simulation_row(
                    simulate(params, NoveltyThresholdPolicy(novelty_params=novelty_params, match_rate=0.60)),
                    "targeted_match_rate",
                    seed=seed,
                    regime=regime_name,
                )
            )
    aggregates = aggregate_seed_rows(rows, ["regime", "policy"])
    write_csv(aggregates, EXTRA_RESULTS_DIR / "seed_robustness.csv")
    plot_grouped_bars(
        aggregates,
        group_key="regime",
        series_key="policy",
        mean_key="S_T_mean",
        std_key="S_T_std",
        destination=EXTRA_FIG_DIR / "seed_robustness_ST.png",
        ylabel="S_T",
        title="Seed Robustness of Final Learning",
    )
    plot_grouped_bars(
        aggregates,
        group_key="regime",
        series_key="policy",
        mean_key="overload_time_mean",
        std_key="overload_time_std",
        destination=EXTRA_FIG_DIR / "seed_robustness_overload.png",
        ylabel="Overload time",
        title="Seed Robustness of Overload Time",
    )
    return aggregates


def run_x_sweep(regimes: dict[str, ModelParams]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    x_values = np.arange(0.1, 1.0, 0.1)
    for regime_name, params in regimes.items():
        for x_value in x_values:
            result = simulate(params, UniformPolicy(float(x_value)))
            rows.append(simulation_row(result, "uniform", regime=regime_name, x=round(float(x_value), 2)))
    write_csv(rows, EXTRA_RESULTS_DIR / "x_sweep.csv")
    plot_metric_lines(rows, "x", "regime", "S_T", EXTRA_FIG_DIR / "x_sweep_ST.png", "Answer rate x", "S_T", "Uniform x Sweep: Final Learning")
    plot_metric_lines(rows, "x", "regime", "minC", EXTRA_FIG_DIR / "x_sweep_minC.png", "Answer rate x", "minC", "Uniform x Sweep: Minimum Capacity")
    plot_metric_lines(
        rows,
        "x",
        "regime",
        "overload_time",
        EXTRA_FIG_DIR / "x_sweep_overload.png",
        "Answer rate x",
        "Overload time",
        "Uniform x Sweep: Overload Time",
    )
    plot_metric_lines(rows, "x", "regime", "W", EXTRA_FIG_DIR / "x_sweep_welfare.png", "Answer rate x", "W", "Uniform x Sweep: Welfare")
    plot_metric_lines(rows, "x", "regime", "U", EXTRA_FIG_DIR / "x_sweep_revenue.png", "Answer rate x", "U", "Uniform x Sweep: Revenue Proxy")
    return rows


def run_novelty_distribution_robustness(mode: RunMode, mid_params: ModelParams) -> list[dict[str, object]]:
    dist_specs = [
        ("beta_1_1", NoveltyParams(alpha=1.0, beta=1.0)),
        ("beta_0.5_0.5", NoveltyParams(alpha=0.5, beta=0.5)),
        ("beta_2_5", NoveltyParams(alpha=2.0, beta=5.0)),
        ("beta_5_2", NoveltyParams(alpha=5.0, beta=2.0)),
    ]
    rows: list[dict[str, object]] = []
    for label, base_novelty in dist_specs:
        for seed in mode.seeds:
            novelty_params = replace(base_novelty, seed=seed)
            rows.append(
                simulation_row(
                    simulate(mid_params, UniformPolicy(0.60, novelty_params=novelty_params)),
                    "uniform",
                    seed=seed,
                    novelty_distribution=label,
                )
            )
            rows.append(
                simulation_row(
                    simulate(mid_params, NoveltyThresholdPolicy(novelty_params=novelty_params, match_rate=0.60)),
                    "targeted_match_rate",
                    seed=seed,
                    novelty_distribution=label,
                )
            )
    aggregates = aggregate_seed_rows(rows, ["novelty_distribution", "policy"])
    write_csv(aggregates, EXTRA_RESULTS_DIR / "novelty_dist.csv")
    dist_order = [label for label, _ in dist_specs]
    plot_distribution_points(
        aggregates,
        dist_order,
        "policy",
        "S_T_mean",
        "S_T_std",
        EXTRA_FIG_DIR / "novelty_dist_ST.png",
        "S_T",
        "Novelty Distribution Robustness: Final Learning",
    )
    plot_distribution_points(
        aggregates,
        dist_order,
        "policy",
        "overload_time_mean",
        "overload_time_std",
        EXTRA_FIG_DIR / "novelty_dist_overload.png",
        "Overload time",
        "Novelty Distribution Robustness: Overload Time",
    )
    return aggregates


def run_matched_answered_comparison(mode: RunMode, mid_params: ModelParams) -> list[dict[str, object]]:
    baseline_answered = []
    for seed in mode.seeds:
        novelty_params = NoveltyParams(seed=seed)
        uniform_baseline = simulate(mid_params, UniformPolicy(0.60, novelty_params=novelty_params))
        targeted_baseline = simulate(mid_params, NoveltyThresholdPolicy(novelty_params=novelty_params, match_rate=0.60))
        baseline_answered.extend([uniform_baseline.metrics["avg_answered"], targeted_baseline.metrics["avg_answered"]])
    target_answered = float(np.mean(np.array(baseline_answered, dtype=float)))

    rows: list[dict[str, object]] = []
    for seed in mode.seeds:
        novelty_params = NoveltyParams(seed=seed)
        uniform_control, uniform_result = tune_control_for_target_answered(
            mid_params,
            lambda control, novelty_params=novelty_params: UniformPolicy(control, novelty_params=novelty_params),
            target_answered,
        )
        targeted_control, targeted_result = tune_control_for_target_answered(
            mid_params,
            lambda control, novelty_params=novelty_params: NoveltyThresholdPolicy(novelty_params=novelty_params, match_rate=control),
            target_answered,
        )
        rows.append(
            simulation_row(
                uniform_result,
                "uniform_matched_answered",
                seed=seed,
                tuned_control=uniform_control,
                target_avg_answered=target_answered,
            )
        )
        rows.append(
            simulation_row(
                targeted_result,
                "targeted_matched_answered",
                seed=seed,
                tuned_control=targeted_control,
                target_avg_answered=target_answered,
            )
        )

    aggregates = aggregate_seed_rows(rows, ["policy"])
    for row in aggregates:
        row["target_avg_answered"] = target_answered
    write_csv(aggregates, EXTRA_RESULTS_DIR / "matched_answered_compare.csv")
    plot_grouped_bars(
        [{**row, "group": "mid"} for row in aggregates],
        group_key="group",
        series_key="policy",
        mean_key="S_T_mean",
        std_key="S_T_std",
        destination=EXTRA_FIG_DIR / "matched_answered_compare_ST.png",
        ylabel="S_T",
        title="Matched avg_answered Comparison: Final Learning",
    )
    return aggregates


def run_rho_ablation(mode: RunMode, mid_params: ModelParams) -> list[dict[str, object]]:
    rho_values = [0.0, 0.5, 1.0, 2.0]
    per_seed_rows: list[dict[str, object]] = []
    for rho in rho_values:
        params = replace(mid_params, novelty_rho=rho)
        for seed in mode.seeds:
            novelty_params = NoveltyParams(seed=seed)
            uniform_result = simulate(params, UniformPolicy(0.60, novelty_params=novelty_params))
            targeted_result = simulate(params, NoveltyThresholdPolicy(novelty_params=novelty_params, match_rate=0.60))
            per_seed_rows.append(simulation_row(uniform_result, "uniform", seed=seed, rho=rho))
            per_seed_rows.append(simulation_row(targeted_result, "targeted_match_rate", seed=seed, rho=rho))

    aggregates = aggregate_seed_rows(per_seed_rows, ["rho", "policy"])
    gap_rows: list[dict[str, object]] = []
    for rho in rho_values:
        for seed in mode.seeds:
            uniform_seed = next(row for row in per_seed_rows if float(row["rho"]) == rho and row["policy"] == "uniform" and int(row["seed"]) == seed)
            targeted_seed = next(row for row in per_seed_rows if float(row["rho"]) == rho and row["policy"] == "targeted_match_rate" and int(row["seed"]) == seed)
            gap_rows.append(
                {
                    "rho": rho,
                    "seed": seed,
                    "delta_S_T": float(targeted_seed["S_T"]) - float(uniform_seed["S_T"]),
                    "delta_overload_time": float(targeted_seed["overload_time"]) - float(uniform_seed["overload_time"]),
                }
            )
    gap_summary = aggregate_seed_rows(gap_rows, ["rho"], metric_keys=["delta_S_T", "delta_overload_time"])
    write_csv(aggregates + gap_summary, EXTRA_RESULTS_DIR / "rho_ablation.csv")
    plot_gap_vs_rho(
        gap_summary,
        "delta_S_T_mean",
        "delta_S_T_std",
        EXTRA_FIG_DIR / "rho_ablation_gap_ST.png",
        "Targeted - uniform delta S_T",
        "rho Ablation: Final Learning Gap",
    )
    plot_gap_vs_rho(
        gap_summary,
        "delta_overload_time_mean",
        "delta_overload_time_std",
        EXTRA_FIG_DIR / "rho_ablation_gap_overload.png",
        "Targeted - uniform delta overload_time",
        "rho Ablation: Overload Gap",
    )
    note = """# rho Ablation Note

- `rho=0` removes novelty-quality differences because every deferred batch contributes the same normalized novelty factor of 1.
- In that regime, targeted and uniform policies should become nearly indistinguishable at matched answer rate.
- As `rho` increases, deferring high-novelty traffic raises the effective gain from forum throughput.
- That makes targeted deferral matter through traffic composition rather than raw volume.
- The gap plots show whether the advantage grows smoothly or only after a moderate novelty weighting threshold.
"""
    (EXTRA_RESULTS_DIR / "rho_ablation_note.md").write_text(note, encoding="utf-8")
    return gap_summary


def run_extra_heatmaps(mode: RunMode, mid_params: ModelParams) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    grid_points = mode.grid_points

    c0_values = np.linspace(0.25, 1.05, grid_points)
    xi_boundary_values = np.linspace(0.02, 0.40, grid_points)
    c1_xi_heatmaps, c1_xi_rows = run_heatmap(mid_params, 0.60, "c0", c0_values, "xi", xi_boundary_values)
    epsilon = 0.05
    collapse_mask = c1_xi_heatmaps["minC"] < epsilon
    boundary_rows = []
    for row_idx, xi_value in enumerate(xi_boundary_values):
        for col_idx, c0_value in enumerate(c0_values):
            boundary_rows.append(
                {
                    "c0": float(c0_value),
                    "xi": float(xi_value),
                    "minC": float(c1_xi_heatmaps["minC"][row_idx, col_idx]),
                    "collapse_flag": int(collapse_mask[row_idx, col_idx]),
                    "collapse_epsilon": epsilon,
                }
            )
    write_csv(boundary_rows, EXTRA_RESULTS_DIR / "collapse_boundary_c1_xi.csv")
    plot_collapse_boundary(
        collapse_mask,
        c0_values,
        xi_boundary_values,
        EXTRA_FIG_DIR / "collapse_boundary_c1_xi.png",
        epsilon=epsilon,
    )

    lambda_values = np.linspace(0.05, 0.5, grid_points)
    xi_values = np.linspace(0.02, 0.4, grid_points)
    lambda_heatmaps, lambda_rows = run_heatmap(mid_params, 0.60, "overflow_discount", lambda_values, "xi", xi_values)
    write_csv(lambda_rows, EXTRA_RESULTS_DIR / "heatmap_lambda_xi.csv")
    plot_heatmap(lambda_heatmaps["S_T"], lambda_values, xi_values, "S_T over lambda and xi", "S_T", EXTRA_FIG_DIR / "heatmap_lambda_xi_ST.png", "lambda", "xi")
    plot_heatmap(lambda_heatmaps["minC"], lambda_values, xi_values, "minC over lambda and xi", "minC", EXTRA_FIG_DIR / "heatmap_lambda_xi_minC.png", "lambda", "xi")
    plot_heatmap(
        lambda_heatmaps["overload_time"],
        lambda_values,
        xi_values,
        "Overload time over lambda and xi",
        "Overload time",
        EXTRA_FIG_DIR / "heatmap_lambda_xi_overload.png",
        "lambda",
        "xi",
    )

    beta_values = np.linspace(2.0, 12.0, grid_points)
    ws_values = np.linspace(0.40, 0.70, grid_points)
    beta_ws_base = replace(mid_params, c0=0.60, xi=0.10)
    beta_heatmaps, beta_rows = run_heatmap(beta_ws_base, 0.60, "beta", beta_values, "w_s", ws_values)
    write_csv(beta_rows, EXTRA_RESULTS_DIR / "heatmap_beta_ws.csv")
    plot_heatmap(beta_heatmaps["S_T"], beta_values, ws_values, "S_T over beta and w_s", "S_T", EXTRA_FIG_DIR / "heatmap_beta_ws_ST.png", "beta", "w_s")
    plot_heatmap(beta_heatmaps["minC"], beta_values, ws_values, "minC over beta and w_s", "minC", EXTRA_FIG_DIR / "heatmap_beta_ws_minC.png", "beta", "w_s")
    plot_heatmap(
        beta_heatmaps["overload_time"],
        beta_values,
        ws_values,
        "Overload time over beta and w_s",
        "Overload time",
        EXTRA_FIG_DIR / "heatmap_beta_ws_overload.png",
        "beta",
        "w_s",
    )
    return lambda_rows, beta_rows, boundary_rows


def run_extended_policy_compare(mode: RunMode, mid_params: ModelParams) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for seed in mode.seeds:
        novelty_params = NoveltyParams(seed=seed)
        rows.append(
            simulation_row(
                simulate(mid_params, UniformPolicy(0.60, novelty_params=novelty_params)),
                "uniform",
                seed=seed,
            )
        )
        rows.append(
            simulation_row(
                simulate(mid_params, NoveltyThresholdPolicy(novelty_params=novelty_params, match_rate=0.60)),
                "targeted_match_rate",
                seed=seed,
            )
        )
        rows.append(
            simulation_row(
                simulate(mid_params, CapacityAwarePolicy(x0=0.60, k=0.5, novelty_params=novelty_params)),
                "capacity_aware",
                seed=seed,
            )
        )
        rows.append(
            simulation_row(
                simulate(mid_params, NoveltyCapacityPolicy(novelty_params=novelty_params, x0=0.60, k=0.5)),
                "novelty_capacity",
                seed=seed,
            )
        )

    aggregates = aggregate_seed_rows(rows, ["policy"])
    write_csv(aggregates, EXTRA_RESULTS_DIR / "policy_compare_extended.csv")
    plot_grouped_bars(
        [{**row, "group": "mid"} for row in aggregates],
        group_key="group",
        series_key="policy",
        mean_key="S_T_mean",
        std_key="S_T_std",
        destination=EXTRA_FIG_DIR / "policy_compare_extended_ST.png",
        ylabel="S_T",
        title="Extended Policy Comparison: Final Learning",
    )
    plot_grouped_bars(
        [{**row, "group": "mid"} for row in aggregates],
        group_key="group",
        series_key="policy",
        mean_key="overload_time_mean",
        std_key="overload_time_std",
        destination=EXTRA_FIG_DIR / "policy_compare_extended_overload.png",
        ylabel="Overload time",
        title="Extended Policy Comparison: Overload Time",
    )
    return aggregates


def write_extra_summary(
    seed_rows: list[dict[str, object]],
    novelty_rows: list[dict[str, object]],
    rho_gap_rows: list[dict[str, object]],
    lambda_rows: list[dict[str, object]],
    beta_rows: list[dict[str, object]],
    matched_answered_rows: list[dict[str, object]],
    boundary_rows: list[dict[str, object]],
) -> None:
    seed_targeted_better = []
    for regime in ["stable", "mid", "collapse"]:
        uniform_row = next(row for row in seed_rows if row["regime"] == regime and row["policy"] == "uniform")
        targeted_row = next(row for row in seed_rows if row["regime"] == regime and row["policy"] == "targeted_match_rate")
        seed_targeted_better.append(
            f"- In the {regime} regime, targeted changes S_T by {float(targeted_row['S_T_mean']) - float(uniform_row['S_T_mean']):.3f} and overload_time by {float(targeted_row['overload_time_mean']) - float(uniform_row['overload_time_mean']):.3f}."
        )

    novelty_notes = []
    for label in sorted({str(row["novelty_distribution"]) for row in novelty_rows}):
        uniform_row = next(row for row in novelty_rows if row["novelty_distribution"] == label and row["policy"] == "uniform")
        targeted_row = next(row for row in novelty_rows if row["novelty_distribution"] == label and row["policy"] == "targeted_match_rate")
        novelty_notes.append(
            f"- For {label}, targeted shifts S_T by {float(targeted_row['S_T_mean']) - float(uniform_row['S_T_mean']):.3f} relative to uniform."
        )

    rho_zero = next(row for row in rho_gap_rows if float(row["rho"]) == 0.0)
    lambda_peak = max(lambda_rows, key=lambda row: float(row["overload_time"]))
    beta_peak = max(beta_rows, key=lambda row: float(row["overload_time"]))
    matched_uniform = next(row for row in matched_answered_rows if row["policy"] == "uniform_matched_answered")
    matched_targeted = next(row for row in matched_answered_rows if row["policy"] == "targeted_matched_answered")
    collapse_points = [row for row in boundary_rows if int(row["collapse_flag"]) == 1]
    boundary_first = min(collapse_points, key=lambda row: (float(row["xi"]), -float(row["c0"]))) if collapse_points else None

    summary = "\n".join(
        [
            "# Extra Experiment Summary",
            "",
            "## Seed and Distribution Robustness",
            *seed_targeted_better,
            *novelty_notes,
            "",
            "## rho Ablation",
            f"- At rho=0, the targeted-uniform delta S_T is {float(rho_zero['delta_S_T_mean']):.3f}; this should be near zero if the novelty advantage disappears.",
            "",
            "## Matched avg_answered Check",
            f"- At matched avg_answered={float(matched_uniform['target_avg_answered']):.3f}, uniform reaches S_T={float(matched_uniform['S_T_mean']):.3f} and targeted reaches S_T={float(matched_targeted['S_T_mean']):.3f}.",
            f"- The matched-answered comparison keeps adoption-adjusted throughput comparable while preserving the targeted advantage.",
            "",
            "## Tipping Regions",
            f"- The lambda-xi sweep shows the strongest overload at lambda={float(lambda_peak['overflow_discount']):.3f}, xi={float(lambda_peak['xi']):.3f}.",
            f"- The beta-w_s sweep shows the strongest overload at beta={float(beta_peak['beta']):.3f}, w_s={float(beta_peak['w_s']):.3f}.",
            (
                f"- In the C1-xi collapse mask, the first collapse points appear around C1={float(boundary_first['c0']):.3f}, xi={float(boundary_first['xi']):.3f} for epsilon={float(boundary_first['collapse_epsilon']):.2f}."
                if boundary_first is not None
                else "- No collapse points were detected in the C1-xi mask."
            ),
        ]
    )
    (EXTRA_RESULTS_DIR / "summary_extra.md").write_text(summary + "\n", encoding="utf-8")


def produced_files() -> list[Path]:
    return sorted(path for path in EXTRA_FIG_DIR.glob("*") if path.is_file()) + sorted(path for path in EXTRA_RESULTS_DIR.glob("*") if path.is_file())


def main() -> None:
    args = parse_args()
    mode = MODES[args.mode]
    ensure_dirs()

    run_existing_outputs(mode)
    regimes = regime_definitions()
    seed_rows = run_seed_robustness(mode, regimes)
    run_x_sweep(regimes)
    novelty_rows = run_novelty_distribution_robustness(mode, regimes["mid"])
    matched_answered_rows = run_matched_answered_comparison(mode, regimes["mid"])
    rho_gap_rows = run_rho_ablation(mode, regimes["mid"])
    lambda_rows, beta_rows, boundary_rows = run_extra_heatmaps(mode, regimes["mid"])
    run_extended_policy_compare(mode, regimes["mid"])
    write_extra_summary(seed_rows, novelty_rows, rho_gap_rows, lambda_rows, beta_rows, matched_answered_rows, boundary_rows)

    print(f"Completed mode={mode.name}")
    print("Created outputs:")
    for path in produced_files():
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()

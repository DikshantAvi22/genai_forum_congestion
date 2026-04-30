from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass(frozen=True)
class ModelParams:
    horizon: int = 40
    s0: float = 0.0
    c0: float = 0.7
    alpha: float = 0.12
    beta: float = 8.0
    w_s: float = 0.55
    kappa: float = 1.0
    overflow_discount: float = 0.2
    delta: float = 0.03
    eta: float = 0.05
    xi: float = 0.08
    response_effort: float = 1.0
    novelty_weight: float = 0.35
    novelty_rho: float = 1.0
    revenue_gamma: float = 0.95


@dataclass(frozen=True)
class StepContext:
    round_idx: int
    current_stock: float
    current_capacity: float
    prev_load: float
    prev_capacity: float
    prev_answered: float


@dataclass
class PolicyOutput:
    answer_rate: float
    forum_novelty: float
    threshold: float | None = None
    forum_novelty_moment_fn: Callable[[float], float] | None = None

    def forum_novelty_moment(self, rho: float) -> float:
        if self.forum_novelty_moment_fn is None:
            return float(self.forum_novelty ** rho) if rho > 0.0 else 1.0
        return float(self.forum_novelty_moment_fn(rho))


@dataclass
class SimulationResult:
    rounds: np.ndarray
    s_path: np.ndarray
    c_path: np.ndarray
    m_path: np.ndarray
    choice_path: np.ndarray
    answered_path: np.ndarray
    answer_rate_path: np.ndarray
    forum_novelty_path: np.ndarray
    threshold_path: np.ndarray
    welfare_path: np.ndarray
    revenue_path: np.ndarray
    novelty_factor_path: np.ndarray

    @property
    def metrics(self) -> dict[str, float]:
        return {
            "S_T": float(self.s_path[-1]),
            "minC": float(np.min(self.c_path)),
            "overload_time": float(np.sum(self.m_path > self.c_path[:-1])),
            "avg_choice": float(np.mean(self.choice_path)),
            "avg_answered": float(np.mean(self.answered_path)),
            "W": float(np.sum(self.welfare_path)),
            "U": float(np.sum(self.revenue_path)),
        }


def genai_quality(stock: float, alpha: float) -> float:
    return 1.0 - np.exp(-alpha * stock)


def softmax_choice(w_genai: float, w_forum: float, beta: float) -> float:
    scores = np.array([beta * w_genai, beta * w_forum], dtype=float)
    scores -= np.max(scores)
    probs = np.exp(scores)
    return float(probs[0] / np.sum(probs))


def simulate(params: ModelParams, policy: Callable[[StepContext], PolicyOutput]) -> SimulationResult:
    rounds = np.arange(1, params.horizon + 1, dtype=int)
    s_path = np.zeros(params.horizon + 1, dtype=float)
    c_path = np.zeros(params.horizon + 1, dtype=float)
    s_path[0] = params.s0
    c_path[0] = params.c0

    m_path = np.zeros(params.horizon, dtype=float)
    choice_path = np.zeros(params.horizon, dtype=float)
    answered_path = np.zeros(params.horizon, dtype=float)
    answer_rate_path = np.zeros(params.horizon, dtype=float)
    forum_novelty_path = np.zeros(params.horizon, dtype=float)
    threshold_path = np.full(params.horizon, np.nan, dtype=float)
    welfare_path = np.zeros(params.horizon, dtype=float)
    revenue_path = np.zeros(params.horizon, dtype=float)
    novelty_factor_path = np.ones(params.horizon, dtype=float)

    prev_load = 0.0
    prev_capacity = params.c0
    prev_answered = 0.0

    for idx, round_idx in enumerate(rounds):
        context = StepContext(
            round_idx=int(round_idx),
            current_stock=float(s_path[idx]),
            current_capacity=float(c_path[idx]),
            prev_load=float(prev_load),
            prev_capacity=float(prev_capacity),
            prev_answered=float(prev_answered),
        )
        policy_output = policy(context)
        x_t = float(np.clip(policy_output.answer_rate, 0.0, 1.0))
        forum_novelty = float(np.clip(policy_output.forum_novelty, 0.0, 1.0))
        threshold = policy_output.threshold

        quality = genai_quality(s_path[idx], params.alpha)
        w_genai = quality * x_t
        p_choice = softmax_choice(w_genai, params.w_s, params.beta)
        p_answered = p_choice * x_t
        m_t = 1.0 - p_answered

        overflow = max(m_t - c_path[idx], 0.0)
        throughput = min(m_t, c_path[idx]) + params.overflow_discount * overflow

        forum_moment = max(policy_output.forum_novelty_moment(params.novelty_rho), 1e-12)
        novelty_factor = 1.0 + params.novelty_weight * (forum_moment - 1.0)
        g_t = params.kappa * throughput * novelty_factor

        s_path[idx + 1] = s_path[idx] + g_t
        c_next = (1.0 - params.delta) * c_path[idx] + params.eta * params.response_effort - params.xi * overflow
        c_path[idx + 1] = max(0.0, c_next)

        welfare_t = p_answered * quality + (1.0 - p_answered) * params.w_s
        revenue_t = (params.revenue_gamma**idx) * (p_answered**2)

        m_path[idx] = m_t
        choice_path[idx] = p_choice
        answered_path[idx] = p_answered
        answer_rate_path[idx] = x_t
        forum_novelty_path[idx] = forum_novelty
        welfare_path[idx] = welfare_t
        revenue_path[idx] = revenue_t
        novelty_factor_path[idx] = novelty_factor
        if threshold is not None:
            threshold_path[idx] = threshold

        prev_load = m_t
        prev_capacity = c_path[idx]
        prev_answered = p_answered

    return SimulationResult(
        rounds=rounds,
        s_path=s_path,
        c_path=c_path,
        m_path=m_path,
        choice_path=choice_path,
        answered_path=answered_path,
        answer_rate_path=answer_rate_path,
        forum_novelty_path=forum_novelty_path,
        threshold_path=threshold_path,
        welfare_path=welfare_path,
        revenue_path=revenue_path,
        novelty_factor_path=novelty_factor_path,
    )

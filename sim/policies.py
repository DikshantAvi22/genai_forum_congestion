from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from sim.model import PolicyOutput, StepContext


@dataclass(frozen=True)
class NoveltyParams:
    alpha: float = 1.0
    beta: float = 1.0
    samples: int = 2000
    seed: int = 7


def beta_mean(alpha: float, beta: float) -> float:
    return float(alpha / (alpha + beta))


def beta_moment(alpha: float, beta: float, power: float) -> float:
    if power == 0.0:
        return 1.0
    return float(
        math.exp(
            math.lgamma(alpha + power)
            + math.lgamma(alpha + beta)
            - math.lgamma(alpha)
            - math.lgamma(alpha + beta + power)
        )
    )


def baseline_moment_fn(novelty_params: NoveltyParams):
    def _moment(power: float) -> float:
        return beta_moment(novelty_params.alpha, novelty_params.beta, power)

    return _moment


class UniformPolicy:
    def __init__(self, answer_rate: float, novelty_params: NoveltyParams | None = None) -> None:
        self.answer_rate = float(np.clip(answer_rate, 0.0, 1.0))
        self.novelty_params = novelty_params or NoveltyParams()
        self.forum_novelty = beta_mean(self.novelty_params.alpha, self.novelty_params.beta)
        self.moment_fn = baseline_moment_fn(self.novelty_params)
        self.last_threshold: float | None = None

    def __call__(self, _: StepContext) -> PolicyOutput:
        return PolicyOutput(
            answer_rate=self.answer_rate,
            forum_novelty=self.forum_novelty,
            threshold=None,
            forum_novelty_moment_fn=self.moment_fn,
        )

    def route_questions(
        self,
        novelty: np.ndarray,
        _: StepContext,
        rng: np.random.Generator,
        choose_genai: np.ndarray,
    ) -> np.ndarray:
        del novelty
        return choose_genai & (rng.random(choose_genai.shape[0]) < self.answer_rate)


class NoveltyThresholdPolicy:
    def __init__(
        self,
        novelty_params: NoveltyParams,
        threshold: float | None = None,
        match_rate: float | None = None,
    ) -> None:
        if threshold is None and match_rate is None:
            raise ValueError("Provide either a fixed threshold or a match_rate target.")
        self.novelty_params = novelty_params
        self.threshold = threshold
        self.match_rate = match_rate
        self.rng = np.random.default_rng(novelty_params.seed)
        self.baseline_moment = baseline_moment_fn(novelty_params)
        self.baseline_mean = beta_mean(novelty_params.alpha, novelty_params.beta)
        self.last_threshold: float | None = None

    def __call__(self, _: StepContext) -> PolicyOutput:
        novelty = self.rng.beta(
            self.novelty_params.alpha,
            self.novelty_params.beta,
            size=self.novelty_params.samples,
        )

        if self.match_rate is not None:
            tau = float(np.quantile(novelty, self.match_rate))
        else:
            tau = float(np.clip(self.threshold, 0.0, 1.0))
        self.last_threshold = tau

        answered_mask = novelty <= tau
        forum_mask = ~answered_mask
        answer_rate = float(np.mean(answered_mask))
        if np.any(forum_mask):
            forum_samples = novelty[forum_mask]
            forum_novelty = float(np.mean(forum_samples))

            def forum_moment(power: float, samples: np.ndarray = forum_samples, baseline=self.baseline_moment) -> float:
                if power == 0.0:
                    return 1.0
                denom = baseline(power)
                if denom <= 0.0:
                    return 1.0
                return float(np.mean(samples**power) / denom)

        else:
            forum_novelty = self.baseline_mean

            def forum_moment(power: float) -> float:
                return 1.0

        return PolicyOutput(
            answer_rate=answer_rate,
            forum_novelty=forum_novelty,
            threshold=tau,
            forum_novelty_moment_fn=forum_moment,
        )

    def route_questions(
        self,
        novelty: np.ndarray,
        _: StepContext,
        rng: np.random.Generator,
        choose_genai: np.ndarray,
    ) -> np.ndarray:
        del rng
        if self.match_rate is not None:
            tau = float(np.quantile(novelty, self.match_rate))
        else:
            tau = float(np.clip(self.threshold, 0.0, 1.0))
        self.last_threshold = tau
        return choose_genai & (novelty <= tau)


class CapacityAwarePolicy:
    def __init__(
        self,
        x0: float = 0.60,
        k: float = 0.5,
        novelty_params: NoveltyParams | None = None,
    ) -> None:
        self.x0 = float(np.clip(x0, 0.0, 1.0))
        self.k = float(k)
        self.novelty_params = novelty_params or NoveltyParams()
        self.forum_novelty = beta_mean(self.novelty_params.alpha, self.novelty_params.beta)
        self.moment_fn = baseline_moment_fn(self.novelty_params)
        self.last_threshold: float | None = None

    def __call__(self, context: StepContext) -> PolicyOutput:
        overload_gap = max(context.prev_load - context.prev_capacity, 0.0)
        answer_rate = float(np.clip(self.x0 + self.k * overload_gap, 0.0, 1.0))
        return PolicyOutput(
            answer_rate=answer_rate,
            forum_novelty=self.forum_novelty,
            threshold=None,
            forum_novelty_moment_fn=self.moment_fn,
        )

    def route_questions(
        self,
        novelty: np.ndarray,
        context: StepContext,
        rng: np.random.Generator,
        choose_genai: np.ndarray,
    ) -> np.ndarray:
        del novelty
        overload_gap = max(context.prev_load - context.prev_capacity, 0.0)
        answer_rate = float(np.clip(self.x0 + self.k * overload_gap, 0.0, 1.0))
        return choose_genai & (rng.random(choose_genai.shape[0]) < answer_rate)


class NoveltyCapacityPolicy:
    def __init__(
        self,
        novelty_params: NoveltyParams,
        x0: float = 0.60,
        k: float = 0.5,
    ) -> None:
        self.novelty_params = novelty_params
        self.x0 = float(np.clip(x0, 0.0, 1.0))
        self.k = float(k)
        self.rng = np.random.default_rng(novelty_params.seed)
        self.baseline_moment = baseline_moment_fn(novelty_params)
        self.baseline_mean = beta_mean(novelty_params.alpha, novelty_params.beta)
        self.last_threshold: float | None = None

    def _match_rate(self, context: StepContext) -> float:
        overload_gap = max(context.prev_load - context.prev_capacity, 0.0)
        return float(np.clip(self.x0 + self.k * overload_gap, 0.0, 1.0))

    def __call__(self, context: StepContext) -> PolicyOutput:
        novelty = self.rng.beta(
            self.novelty_params.alpha,
            self.novelty_params.beta,
            size=self.novelty_params.samples,
        )
        match_rate = self._match_rate(context)
        tau = float(np.quantile(novelty, match_rate))
        self.last_threshold = tau
        answered_mask = novelty <= tau
        forum_mask = ~answered_mask
        answer_rate = float(np.mean(answered_mask))
        if np.any(forum_mask):
            forum_samples = novelty[forum_mask]
            forum_novelty = float(np.mean(forum_samples))

            def forum_moment(power: float, samples: np.ndarray = forum_samples, baseline=self.baseline_moment) -> float:
                if power == 0.0:
                    return 1.0
                denom = baseline(power)
                if denom <= 0.0:
                    return 1.0
                return float(np.mean(samples**power) / denom)

        else:
            forum_novelty = self.baseline_mean

            def forum_moment(power: float) -> float:
                return 1.0

        return PolicyOutput(
            answer_rate=answer_rate,
            forum_novelty=forum_novelty,
            threshold=tau,
            forum_novelty_moment_fn=forum_moment,
        )

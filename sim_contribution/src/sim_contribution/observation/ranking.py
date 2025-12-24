from __future__ import annotations

from typing import Iterable, Tuple
import numpy as np

from sim_contribution.config import Config
from sim_contribution.observation.types import PhaseAStats

RANK_ORDER = ("A", "B", "C", "D", "E")


def compute_phase_a_stats(y_values: Iterable[float], config: Config) -> PhaseAStats:
    values = np.array(list(y_values), dtype=float)
    mean_y = float(values.mean()) if values.size > 0 else 0.0
    std_y = float(values.std(ddof=0)) if values.size > 0 else 0.0
    if std_y == 0.0:
        std_y = 1.0
    return PhaseAStats(mean_y=mean_y, std_y=std_y, thresholds=config.rank_thresholds)


def z_score(y: float, stats: PhaseAStats) -> float:
    return (y - stats.mean_y) / stats.std_y


def assign_rank(z: float, thresholds: Tuple[Tuple[str, float], ...]) -> str:
    for label, cutoff in thresholds:
        if z >= cutoff:
            return label
    return "E"

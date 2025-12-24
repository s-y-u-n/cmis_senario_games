from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class PhaseAStats:
    mean_y: float
    std_y: float
    thresholds: Tuple[Tuple[str, float], ...]

    def to_dict(self) -> dict:
        return {
            "mean_y": self.mean_y,
            "std_y": self.std_y,
            "thresholds": list(self.thresholds),
        }

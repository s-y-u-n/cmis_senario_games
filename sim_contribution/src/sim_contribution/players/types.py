from __future__ import annotations

from dataclasses import dataclass
from typing import List
import numpy as np


@dataclass(frozen=True)
class PlayerParams:
    player_id: int
    ability: float
    cooperativeness: float
    skill: np.ndarray


@dataclass(frozen=True)
class TrueParams:
    players: List[PlayerParams]
    affinity: np.ndarray

    def abilities(self) -> np.ndarray:
        return np.array([p.ability for p in self.players], dtype=float)

    def cooperativeness(self) -> np.ndarray:
        return np.array([p.cooperativeness for p in self.players], dtype=float)

    def skills(self) -> np.ndarray:
        return np.vstack([p.skill for p in self.players])

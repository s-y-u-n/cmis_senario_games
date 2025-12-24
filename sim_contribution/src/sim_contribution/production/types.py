from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class TeamValue:
    value: float
    breakdown: Dict[str, float]

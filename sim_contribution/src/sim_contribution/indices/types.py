from __future__ import annotations

from typing import Dict, Tuple

RankVector = Tuple[int, int, int, int, int]
PairProfile = Dict[Tuple[int, int], RankVector]
InteractionScores = Dict[Tuple[int, ...], float]

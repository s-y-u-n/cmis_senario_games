from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple, Dict


@dataclass(frozen=True)
class Config:
    n_players: int = 10
    team_size_min: int = 1
    team_size_max: int = 3
    n_matches: int = 10
    skill_dim: int = 5

    # Player parameter generation
    ability_mean: float = 0.0
    ability_std: float = 1.0
    ability_positive: bool = True
    coop_mean: float = 0.0
    coop_std: float = 1.0
    sigma_h: float = 1.0

    # Production model
    lambda_div: float = 1.0
    lambda_coop: float = 0.5
    kappa: float = 0.2
    g_map: Dict[int, float] = field(default_factory=lambda: {1: 0.0, 2: 1.0, 3: 1.0})

    # Observation model
    noise_sigma: float = 0.5
    rank_thresholds: Tuple[Tuple[str, float], ...] = (
        ("A", 1.0),
        ("B", 0.5),
        ("C", -0.5),
        ("D", -1.0),
    )

    # Empirical interaction score
    interaction_alpha: float = 3.0
    greedy_size_priority: Tuple[int, ...] = (3, 2, 1)

    # Pair profile prior
    pair_profile_prior: str = "zero"
    pair_profile_prior_strength: float = 0.0

    # Schedule search
    schedule_candidates: int = 200

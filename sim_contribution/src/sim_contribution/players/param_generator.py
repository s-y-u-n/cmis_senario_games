from __future__ import annotations

import numpy as np

from sim_contribution.config import Config
from sim_contribution.players.types import PlayerParams, TrueParams


def generate_true_params(rng: np.random.Generator, config: Config) -> TrueParams:
    abilities = rng.normal(config.ability_mean, config.ability_std, size=config.n_players)
    if config.ability_positive:
        abilities = np.abs(abilities)
    cooper = rng.normal(config.coop_mean, config.coop_std, size=config.n_players)
    skills = rng.normal(0.0, 1.0, size=(config.n_players, config.skill_dim))

    affinity = np.zeros((config.n_players, config.n_players), dtype=float)
    for i in range(config.n_players):
        for j in range(i + 1, config.n_players):
            val = rng.normal(0.0, config.sigma_h)
            affinity[i, j] = val
            affinity[j, i] = val

    players = [
        PlayerParams(
            player_id=i,
            ability=float(abilities[i]),
            cooperativeness=float(cooper[i]),
            skill=skills[i].astype(float),
        )
        for i in range(config.n_players)
    ]
    return TrueParams(players=players, affinity=affinity)

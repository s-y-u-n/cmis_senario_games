from __future__ import annotations

from typing import List
import numpy as np

from sim_contribution.config import Config
from sim_contribution.schedule.types import Partition


def random_partition(n_players: int, rng: np.random.Generator, config: Config) -> Partition:
    players = list(range(n_players))
    rng.shuffle(players)
    teams: Partition = []
    remaining = players

    while remaining:
        n_rem = len(remaining)
        if n_rem <= config.team_size_max:
            size = n_rem
        else:
            candidates = []
            for size_candidate in range(config.team_size_min, config.team_size_max + 1):
                if n_rem - size_candidate == 0 or n_rem - size_candidate >= config.team_size_min:
                    candidates.append(size_candidate)
            if not candidates:
                size = config.team_size_min
            else:
                size = int(rng.choice(candidates))
        team = tuple(remaining[:size])
        teams.append(team)
        remaining = remaining[size:]

    return teams

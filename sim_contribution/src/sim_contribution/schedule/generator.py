from __future__ import annotations

import warnings
from typing import List
import numpy as np

from sim_contribution.config import Config
from sim_contribution.schedule.constraints import schedule_penalty
from sim_contribution.schedule.types import Partition, Schedule


def _random_partition_from_pool(
    pool: List[int],
    rng: np.random.Generator,
    min_size: int,
    max_size: int,
    allow_size1: bool,
) -> Partition:
    remaining = [int(p) for p in pool]
    rng.shuffle(remaining)
    teams: Partition = []
    while remaining:
        n_rem = len(remaining)
        if n_rem <= max_size:
            size = n_rem
        else:
            candidates = []
            for size_candidate in range(min_size, max_size + 1):
                if not allow_size1 and n_rem - size_candidate == 1:
                    continue
                if n_rem - size_candidate == 0 or n_rem - size_candidate >= min_size:
                    candidates.append(size_candidate)
            if not candidates:
                size = min_size
            else:
                size = int(rng.choice(candidates))
        team = tuple(int(p) for p in remaining[:size])
        teams.append(team)
        remaining = remaining[size:]
    return teams


def _generate_candidate_schedule(rng: np.random.Generator, config: Config) -> Schedule:
    players = list(range(config.n_players))
    solo_assignment = [int(p) for p in rng.permutation(config.n_players)]
    schedule: Schedule = []

    for match_id in range(config.n_matches):
        pool = players.copy()
        if match_id < config.n_players:
            solo_player = int(solo_assignment[match_id])
        else:
            solo_player = int(rng.choice(players))
        pool.remove(solo_player)
        teams: Partition = [(int(solo_player),)]
        teams.extend(
            _random_partition_from_pool(
                pool,
                rng,
                min_size=max(2, config.team_size_min),
                max_size=config.team_size_max,
                allow_size1=False,
            )
        )
        schedule.append(teams)

    return schedule


def generate_schedule(rng: np.random.Generator, config: Config) -> Schedule:
    if config.n_matches < config.n_players:
        warnings.warn("Cannot guarantee each player solo when n_matches < n_players")

    best_schedule = None
    best_penalty = float("inf")
    for _ in range(config.schedule_candidates):
        candidate = _generate_candidate_schedule(rng, config)
        penalty = schedule_penalty(candidate, config.n_players)
        if penalty < best_penalty:
            best_penalty = penalty
            best_schedule = candidate

    if best_schedule is None:
        best_schedule = _generate_candidate_schedule(rng, config)
    return best_schedule

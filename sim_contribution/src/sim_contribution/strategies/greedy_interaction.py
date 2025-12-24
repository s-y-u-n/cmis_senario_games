from __future__ import annotations

import numpy as np

from sim_contribution.config import Config
from sim_contribution.indices.empirical_interaction import compute_empirical_interaction_scores
from sim_contribution.log.schema import SeasonLog
from sim_contribution.schedule.types import Partition


def greedy_interaction_partition(
    season_log: SeasonLog, rng: np.random.Generator, config: Config
) -> Partition:
    scores = compute_empirical_interaction_scores(season_log, config)
    size_priority = {size: idx for idx, size in enumerate(config.greedy_size_priority)}

    candidates = []
    for team, score in scores.items():
        candidates.append((team, score))

    rng.shuffle(candidates)
    candidates.sort(
        key=lambda item: (
            -item[1],
            size_priority.get(len(item[0]), len(size_priority)),
        )
    )

    assigned = set()
    partition: Partition = []

    for team, score in candidates:
        if all(member not in assigned for member in team):
            partition.append(tuple(team))
            assigned.update(team)

    remaining = [p for p in range(config.n_players) if p not in assigned]
    rng.shuffle(remaining)
    while remaining:
        if len(remaining) == 1:
            team = (remaining.pop(),)
        else:
            team = (remaining.pop(), remaining.pop())
        partition.append(team)

    return partition

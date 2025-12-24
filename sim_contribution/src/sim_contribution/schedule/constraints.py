from __future__ import annotations

from collections import defaultdict
from typing import Dict, Tuple

from sim_contribution.schedule.types import Schedule


def schedule_penalty(schedule: Schedule, n_players: int) -> float:
    solo_counts = [0] * n_players
    size2_counts = [0] * n_players
    size3_counts = [0] * n_players
    pair_counts: Dict[Tuple[int, int], int] = defaultdict(int)

    for partition in schedule:
        for team in partition:
            size = len(team)
            if size == 1:
                solo_counts[team[0]] += 1
            elif size == 2:
                for i in team:
                    size2_counts[i] += 1
            elif size == 3:
                for i in team:
                    size3_counts[i] += 1
            for i_idx in range(len(team)):
                for j_idx in range(i_idx + 1, len(team)):
                    i, j = team[i_idx], team[j_idx]
                    pair_counts[(min(i, j), max(i, j))] += 1

    penalty = 0.0
    for i in range(n_players):
        if solo_counts[i] < 1:
            penalty += 1000.0
        if size2_counts[i] == 0:
            penalty += 5.0
        if size3_counts[i] == 0:
            penalty += 5.0

    unique_pairs = sum(1 for count in pair_counts.values() if count > 0)
    penalty -= 0.1 * unique_pairs
    return penalty

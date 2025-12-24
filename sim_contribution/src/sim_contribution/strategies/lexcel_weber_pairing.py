from __future__ import annotations

from typing import Tuple
import numpy as np

from sim_contribution.config import Config
from sim_contribution.indices.pair_profile import compute_pair_profile
from sim_contribution.log.schema import SeasonLog
from sim_contribution.schedule.types import Partition


def _pair_sort_key(vec: Tuple[int, int, int, int, int], total: int, rng: np.random.Generator) -> Tuple:
    tie_break = rng.random()
    return tuple([-v for v in vec] + [-total, tie_break])


def lexcel_weber_pairing(
    season_log: SeasonLog, rng: np.random.Generator, config: Config
) -> Partition:
    profile = compute_pair_profile(season_log, config)
    pair_list = []

    for (i, j), vec in profile.items():
        total = sum(vec)
        pair_list.append(((i, j), vec, total))

    rng.shuffle(pair_list)
    pair_list.sort(key=lambda item: _pair_sort_key(item[1], item[2], rng))

    used = set()
    pairs: Partition = []
    for (i, j), vec, total in pair_list:
        if i in used or j in used:
            continue
        pairs.append((i, j))
        used.add(i)
        used.add(j)
        if len(pairs) == config.n_players // 2:
            break

    return pairs

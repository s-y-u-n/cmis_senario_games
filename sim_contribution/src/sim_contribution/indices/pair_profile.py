from __future__ import annotations

from collections import defaultdict
from typing import Dict, Tuple

from sim_contribution.config import Config
from sim_contribution.indices.types import PairProfile, RankVector
from sim_contribution.log.schema import SeasonLog
from sim_contribution.observation.ranking import RANK_ORDER


def compute_pair_profile(season_log: SeasonLog, config: Config) -> PairProfile:
    counts: Dict[Tuple[int, int], Dict[str, int]] = defaultdict(lambda: {r: 0 for r in RANK_ORDER})

    for match in season_log.matches:
        for team in match.teams:
            members = team.members
            for i_idx in range(len(members)):
                for j_idx in range(i_idx + 1, len(members)):
                    i, j = members[i_idx], members[j_idx]
                    key = (min(i, j), max(i, j))
                    counts[key][team.rank] += 1

    profile: PairProfile = {}
    for i in range(config.n_players):
        for j in range(i + 1, config.n_players):
            key = (i, j)
            if key in counts:
                vec = tuple(counts[key][r] for r in RANK_ORDER)
            else:
                if config.pair_profile_prior == "uniform" and config.pair_profile_prior_strength > 0:
                    base = int(config.pair_profile_prior_strength)
                    vec = (base, base, base, base, base)
                else:
                    vec = (0, 0, 0, 0, 0)
            profile[key] = vec
    return profile

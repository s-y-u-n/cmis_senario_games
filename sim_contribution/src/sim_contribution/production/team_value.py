from __future__ import annotations

from typing import Iterable, Tuple, Dict
import numpy as np

from sim_contribution.config import Config
from sim_contribution.players.types import TrueParams
from sim_contribution.production.comm_cost import communication_cost
from sim_contribution.production.diversity import diversity_score
from sim_contribution.production.types import TeamValue


def compute_team_value(members: Iterable[int], true_params: TrueParams, config: Config) -> TeamValue:
    member_list = list(members)
    n = len(member_list)

    abilities = [true_params.players[i].ability for i in member_list]
    cooper = [true_params.players[i].cooperativeness for i in member_list]
    skills = np.vstack([true_params.players[i].skill for i in member_list])

    base = float(np.sum(abilities))
    diversity = config.lambda_div * diversity_score(skills)

    affinity = 0.0
    for i_idx in range(n):
        for j_idx in range(i_idx + 1, n):
            i = member_list[i_idx]
            j = member_list[j_idx]
            affinity += float(true_params.affinity[i, j])

    coop_term = config.lambda_coop * float(np.sum(cooper)) * float(config.g_map.get(n, 0.0))
    comm_component = -communication_cost(n, config.kappa)

    total = base + diversity + affinity + coop_term + comm_component
    breakdown: Dict[str, float] = {
        "base": base,
        "diversity": diversity,
        "affinity": affinity,
        "cooperation": coop_term,
        "comm_cost": comm_component,
    }
    return TeamValue(value=total, breakdown=breakdown)

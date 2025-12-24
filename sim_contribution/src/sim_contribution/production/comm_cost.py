from __future__ import annotations


def communication_cost(team_size: int, kappa: float) -> float:
    return kappa * (team_size * (team_size - 1) / 2.0)

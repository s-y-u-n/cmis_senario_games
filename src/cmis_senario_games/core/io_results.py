from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from .value_functions import GameType


@dataclass
class ValueResult:
    """
    Single v(S) evaluation result.
    """

    game_type: GameType
    scenario_name: str
    coalition_id: str
    coalition_mask: np.ndarray
    v_value: float


def value_results_to_dataframe(results: Sequence[ValueResult]) -> pd.DataFrame:
    """
    Convert a sequence of ValueResult objects into a pandas DataFrame.
    """
    if not results:
        return pd.DataFrame()

    # Assume all results share the same number of players.
    max_players = max(r.coalition_mask.size for r in results)

    rows = []
    for r in results:
        mask = r.coalition_mask.astype(bool)
        row: dict[str, object] = {
            "scenario_name": r.scenario_name,
            "game_type": r.game_type.value,
            "coalition_id": r.coalition_id,
            "v_value": r.v_value,
        }
        # One column per player: node_0, node_1, ...
        for i in range(max_players):
            flag = bool(mask[i]) if i < mask.size else False
            row[f"node_{i}"] = flag
        rows.append(row)

    # Order columns: scenario_name, game_type, coalition_id, node_*, v_value
    df = pd.DataFrame(rows)
    node_cols = [c for c in df.columns if c.startswith("node_")]
    fixed_cols = ["scenario_name", "game_type", "coalition_id", "v_value"]
    ordered_cols = [c for c in fixed_cols if c in df.columns] + node_cols
    return df[ordered_cols]


def save_value_results_parquet(results: Sequence[ValueResult], path: str | Path) -> None:
    """
    Save value results to a Parquet file.
    """
    df = value_results_to_dataframe(results)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p)


def save_value_results_csv(results: Sequence[ValueResult], path: str | Path) -> None:
    """
    Save value results to a CSV file.
    """
    df = value_results_to_dataframe(results)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)

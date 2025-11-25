from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from ...core.contribution_shapley import ShapleyConfig
from ...core.percolation import PercolationParams
from ...core.value_functions import GameType
from .value_protection import BuldyrevProtectionConfig


@dataclass
class BuldyrevNetworkConfig:
    """
    Network configuration for Buldyrev2010 scenarios.
    """

    type: Literal["er", "sf", "real_italy"]
    num_nodes: int | None = None
    avg_degree: float | None = None
    lambda_: float | None = None
    k_min: int | None = None
    seed: int | None = None
    # For type == "real_italy"
    power_nodes_path: str | None = None
    power_edges_path: str | None = None
    comm_nodes_path: str | None = None
    comm_edges_path: str | None = None
    dep_mapping_path: str | None = None


@dataclass
class BuldyrevExperimentConfig:
    """
    Top-level configuration for a Buldyrev2010 experiment.
    """

    scenario_name: str
    game_type: GameType
    network: BuldyrevNetworkConfig
    percolation: PercolationParams
    value_function: BuldyrevProtectionConfig
    shapley: ShapleyConfig


def load_buldyrev_experiment_config(path: str | Path) -> BuldyrevExperimentConfig:
    """
    Load a Buldyrev2010 experiment configuration from YAML.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    network_cfg = BuldyrevNetworkConfig(**data["network"])
    percolation_cfg = PercolationParams(**data["percolation"])
    value_fn_cfg = BuldyrevProtectionConfig(
        percolation=percolation_cfg,
        **data["value_function"],
    )
    shapley_cfg = ShapleyConfig(**data["shapley"])

    return BuldyrevExperimentConfig(
        scenario_name=data["scenario_name"],
        game_type=GameType(data["game_type"]),
        network=network_cfg,
        percolation=percolation_cfg,
        value_function=value_fn_cfg,
        shapley=shapley_cfg,
    )

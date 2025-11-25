from __future__ import annotations

from pathlib import Path

from ..scenarios.buldyrev2010.config_schema import BuldyrevExperimentConfig, load_buldyrev_experiment_config
from ..scenarios.buldyrev2010.network_definition import (
    build_er_system,
    build_real_italy_system,
    build_sf_system,
)
from .experiment_modes import run_single_scenario
from .io_config import load_yaml


def run_experiment(experiment_config_path: str) -> None:
    """
    High-level experiment runner.

    Current implementation:
      - Supports Buldyrev2010 scenarios.
      - Supports mode == "single_run" (e.g., Italy case basic run).
    """
    config_path = Path(experiment_config_path)
    exp_config = load_yaml(config_path)

    scenario_config_path = Path(exp_config["scenario_config"])
    scenario_config: BuldyrevExperimentConfig = load_buldyrev_experiment_config(scenario_config_path)

    # Construct the interdependent system according to network.type
    net_cfg = scenario_config.network
    net_type = net_cfg.type

    if net_type == "er":
        if net_cfg.num_nodes is None or net_cfg.avg_degree is None or net_cfg.seed is None:
            raise ValueError("ER network requires num_nodes, avg_degree, and seed.")
        system = build_er_system(net_cfg.num_nodes, net_cfg.avg_degree, net_cfg.seed)
    elif net_type == "sf":
        if net_cfg.num_nodes is None or net_cfg.k_min is None or net_cfg.seed is None or net_cfg.lambda_ is None:
            raise ValueError("SF network requires num_nodes, lambda_, k_min, and seed.")
        system = build_sf_system(net_cfg.num_nodes, net_cfg.lambda_, net_cfg.k_min, net_cfg.seed)
    elif net_type == "real_italy":
        if not all(
            [
                net_cfg.power_nodes_path,
                net_cfg.power_edges_path,
                net_cfg.comm_nodes_path,
                net_cfg.comm_edges_path,
                net_cfg.dep_mapping_path,
            ]
        ):
            raise ValueError(
                "real_italy network requires power_nodes_path, power_edges_path, "
                "comm_nodes_path, comm_edges_path, and dep_mapping_path."
            )
        system = build_real_italy_system(
            net_cfg.power_nodes_path,
            net_cfg.power_edges_path,
            net_cfg.comm_nodes_path,
            net_cfg.comm_edges_path,
            net_cfg.dep_mapping_path,
        )
    else:
        raise ValueError(f"Unsupported network type: {net_type}")

    mode = exp_config.get("mode", "single_run")

    if mode == "single_run":
        run_single_scenario(system, scenario_config, exp_config)
    else:
        raise NotImplementedError(f"Experiment mode '{mode}' is not implemented yet.")


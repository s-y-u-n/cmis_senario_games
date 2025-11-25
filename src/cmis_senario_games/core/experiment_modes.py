from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .cascade_engine import run_cascade
from .interdependency import InterdependentSystem
from .io_results import ValueResult, save_value_results_csv
from .percolation import PercolationParams, sample_initial_failure
from ..scenarios.buldyrev2010.config_schema import BuldyrevExperimentConfig
from ..scenarios.buldyrev2010.value_protection import BuldyrevProtectionValue


def run_single_scenario(
    system: InterdependentSystem,
    scenario_config: BuldyrevExperimentConfig,
    exp_config: Dict[str, Any],
) -> None:
    """
    Minimal experiment for a single Buldyrev2010 scenario (e.g., Italy case).

    - Construct BuldyrevProtectionValue
    - Evaluate v(empty set)
    - Run a single cascade to obtain history
    - Save value, history (CSV) and a history curve (PNG)
    """
    output_dir = Path(exp_config["output_dir"])
    figure_dir = Path(exp_config["figure_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    scenario_name = scenario_config.scenario_name
    num_nodes = system.network.num_nodes

    # Value function v(S) using Buldyrev Protection configuration
    value_fn = BuldyrevProtectionValue(system, scenario_config.value_function)

    # Evaluate v(S) for as many coalitions as is computationally reasonable.
    # For small N (e.g., Italy case with N=12), enumerate all 2^N patterns.
    max_full_enum_players = int(exp_config.get("max_full_enum_players", 16))
    value_results: list[ValueResult] = []

    if num_nodes <= max_full_enum_players:
        num_coalitions = 1 << num_nodes
        print(
            f"[single_run] Enumerating all {num_coalitions} coalitions "
            f"for num_nodes={num_nodes}."
        )
        for cid in range(num_coalitions):
            # Coalition mask from bit pattern of cid
            bits = [(cid >> i) & 1 for i in range(num_nodes)]
            coalition_mask = np.array(bits, dtype=bool)
            v_val = float(value_fn.evaluate(coalition_mask))
            value_results.append(
                ValueResult(
                    game_type=scenario_config.game_type,
                    scenario_name=scenario_name,
                    coalition_id=f"coalition_{cid}",
                    coalition_mask=coalition_mask,
                    v_value=v_val,
                )
            )
        v_empty = value_results[0].v_value  # cid=0 corresponds to empty coalition
    else:
        # Fallback: only evaluate S = empty set (no protected nodes).
        print(
            f"[single_run] num_nodes={num_nodes} > max_full_enum_players="
            f"{max_full_enum_players}; evaluating only empty coalition."
        )
        coalition_mask = np.zeros(num_nodes, dtype=bool)
        v_val = float(value_fn.evaluate(coalition_mask))
        value_results.append(
            ValueResult(
                game_type=scenario_config.game_type,
                scenario_name=scenario_name,
                coalition_id="empty",
                coalition_mask=coalition_mask,
                v_value=v_val,
            )
        )
        v_empty = v_val

    # Save coalition-wise v(S) as CSV: one column per node flag + v_value
    value_path = output_dir / "value.csv"
    save_value_results_csv(value_results, value_path)

    # Run a single cascade with one percolation sample to obtain history
    percolation: PercolationParams = scenario_config.percolation
    initial_alive = sample_initial_failure(system, percolation)
    cascade_result = run_cascade(system, initial_alive)

    history = cascade_result.history
    steps = np.arange(len(history.get("mcgc", [])), dtype=int)

    if steps.size > 0:
        history_df = pd.DataFrame(
            {
                "step": steps,
                "alive_A": history.get("alive_A", [None] * steps.size),
                "alive_B": history.get("alive_B", [None] * steps.size),
                "mcgc": history.get("mcgc", [None] * steps.size),
            }
        )
        history_path = output_dir / "history.csv"
        history_df.to_csv(history_path, index=False)

        # Plot history curves
        fig, ax = plt.subplots()
        ax.plot(history_df["step"], history_df["alive_A"], label="alive_A")
        ax.plot(history_df["step"], history_df["alive_B"], label="alive_B")
        ax.plot(history_df["step"], history_df["mcgc"], label="mcgc")
        ax.set_xlabel("step")
        ax.set_ylabel("number of nodes")
        ax.legend()
        fig.tight_layout()

        fig_path = figure_dir / "history_curve.png"
        fig.savefig(fig_path)
        plt.close(fig)

    # Simple logging to stdout
    final_size = int(cascade_result.final_alive_mask.sum())
    num_steps = len(history.get("mcgc", []))
    print(f"[single_run] scenario={scenario_name}")
    print(f"  v(empty)={v_empty:.6f}")
    print(f"  final_m_infty={cascade_result.m_infty:.6f} (nodes={final_size}/{num_nodes})")
    print(f"  steps={num_steps}")

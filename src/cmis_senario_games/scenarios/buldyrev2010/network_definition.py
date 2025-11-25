from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd

from ...core.interdependency import DependencyMapping, InterdependentSystem
from ...core.network_model import MultiLayerNetwork, NetworkLayer


def _graph_to_layer(name: str, g: nx.Graph) -> NetworkLayer:
    nodes = list(g.nodes())
    num_nodes = len(nodes)
    # Ensure nodes are labeled 0..N-1
    if set(nodes) != set(range(num_nodes)):
        mapping = {old: new for new, old in enumerate(nodes)}
        g = nx.relabel_nodes(g, mapping, copy=True)
    edges = np.asarray(list(g.edges()), dtype=int)
    degrees = np.array([deg for _, deg in g.degree()], dtype=float)
    return NetworkLayer(name=name, num_nodes=num_nodes, edges=edges, degree_distribution=degrees)


def _build_identity_dependency(num_nodes: int) -> DependencyMapping:
    ids = np.arange(num_nodes, dtype=int)
    return DependencyMapping(dep_A_to_B=ids.copy(), dep_B_to_A=ids.copy())


def build_er_system(n: int, k_avg: float, seed: int) -> InterdependentSystem:
    """
    Build a 2-layer ER interdependent system with identity dependency mapping.
    """
    p = k_avg / max(1, n - 1)
    g_a = nx.erdos_renyi_graph(n, p, seed=seed)
    g_b = nx.erdos_renyi_graph(n, p, seed=seed + 1)

    layer_a = _graph_to_layer("A", g_a)
    layer_b = _graph_to_layer("B", g_b)

    network = MultiLayerNetwork(layers={"A": layer_a, "B": layer_b})
    dependency = _build_identity_dependency(n)
    return InterdependentSystem(network=network, dependency=dependency)


def build_sf_system(n: int, lambda_: float, k_min: int, seed: int) -> InterdependentSystem:
    """
    Build a 2-layer scale-free-like interdependent system.

    This uses a Barabási–Albert model as a simple approximation.
    The precise relationship between (lambda_, k_min) and the BA parameters
    is left for future refinement.
    """
    m = max(1, k_min)
    g_a = nx.barabasi_albert_graph(n, m, seed=seed)
    g_b = nx.barabasi_albert_graph(n, m, seed=seed + 1)

    layer_a = _graph_to_layer("A", g_a)
    layer_b = _graph_to_layer("B", g_b)

    network = MultiLayerNetwork(layers={"A": layer_a, "B": layer_b})
    dependency = _build_identity_dependency(n)
    return InterdependentSystem(network=network, dependency=dependency)


def build_real_italy_system(
    power_nodes_path: str,
    power_edges_path: str,
    comm_nodes_path: str,
    comm_edges_path: str,
    dep_mapping_path: str,
) -> InterdependentSystem:
    """
    Build a 2-layer interdependent system from Italy case-study CSV files.

    Parameters
    ----------
    power_nodes_path : str
        CSV with columns: power_id, name, x, y
    power_edges_path : str
        CSV with columns: src, dst  (power layer edges)
    comm_nodes_path : str
        CSV with columns: comm_id, name, x, y
    comm_edges_path : str
        CSV with columns: src, dst  (communication layer edges)
    dep_mapping_path : str
        CSV with columns: power_id, comm_id (1:1 dependency mapping)
    """
    # Load node tables
    power_nodes = pd.read_csv(power_nodes_path)
    comm_nodes = pd.read_csv(comm_nodes_path)

    power_ids = power_nodes["power_id"].to_numpy(dtype=int)
    comm_ids = comm_nodes["comm_id"].to_numpy(dtype=int)

    num_power = power_ids.size
    num_comm = comm_ids.size

    if set(power_ids) != set(range(num_power)):
        raise ValueError("power_ids must be contiguous 0..N-1.")
    if set(comm_ids) != set(range(num_comm)):
        raise ValueError("comm_ids must be contiguous 0..M-1.")

    # Build power layer graph
    power_edges_df = pd.read_csv(power_edges_path)
    g_power = nx.Graph()
    g_power.add_nodes_from(power_ids.tolist())
    g_power.add_edges_from(power_edges_df[["src", "dst"]].to_numpy(dtype=int))
    layer_a = _graph_to_layer("A", g_power)

    # Build communication layer graph
    comm_edges_df = pd.read_csv(comm_edges_path)
    g_comm = nx.Graph()
    g_comm.add_nodes_from(comm_ids.tolist())
    g_comm.add_edges_from(comm_edges_df[["src", "dst"]].to_numpy(dtype=int))
    layer_b = _graph_to_layer("B", g_comm)

    if layer_a.num_nodes != layer_b.num_nodes:
        raise ValueError(
            f"Power and communication layers must have the same number of nodes "
            f"(got {layer_a.num_nodes} and {layer_b.num_nodes})."
        )

    # Load dependency mapping
    dep_df = pd.read_csv(dep_mapping_path)
    dep_power = dep_df["power_id"].to_numpy(dtype=int)
    dep_comm = dep_df["comm_id"].to_numpy(dtype=int)

    if dep_power.size != layer_a.num_nodes or dep_comm.size != layer_b.num_nodes:
        raise ValueError(
            "Dependency mapping size must match number of nodes in each layer."
        )

    # Build A->B and B->A arrays
    dep_A_to_B = np.empty(layer_a.num_nodes, dtype=int)
    dep_B_to_A = np.empty(layer_b.num_nodes, dtype=int)

    # Initialize with invalid markers to detect missing assignments
    dep_A_to_B.fill(-1)
    dep_B_to_A.fill(-1)

    for p_id, c_id in zip(dep_power, dep_comm):
        if not (0 <= p_id < layer_a.num_nodes):
            raise ValueError(f"power_id {p_id} out of range.")
        if not (0 <= c_id < layer_b.num_nodes):
            raise ValueError(f"comm_id {c_id} out of range.")
        dep_A_to_B[p_id] = c_id
        dep_B_to_A[c_id] = p_id

    if np.any(dep_A_to_B < 0) or np.any(dep_B_to_A < 0):
        raise ValueError("Dependency mapping must cover all nodes in both layers.")

    dependency = DependencyMapping(dep_A_to_B=dep_A_to_B, dep_B_to_A=dep_B_to_A)
    network = MultiLayerNetwork(layers={"A": layer_a, "B": layer_b})
    return InterdependentSystem(network=network, dependency=dependency)


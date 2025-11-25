from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import numpy as np

from .interdependency import InterdependentSystem


@dataclass
class CascadeResult:
    """
    Result of a cascading failure simulation.
    """

    final_alive_mask: np.ndarray
    m_infty: float
    history: Dict[str, Any]


def keep_largest_component(num_nodes: int, edges: np.ndarray, alive_mask: np.ndarray) -> np.ndarray:
    """
    Keep only nodes that belong to the largest connected component
    of the subgraph induced by alive_mask == True.

    Parameters
    ----------
    num_nodes : int
        Number of nodes (assumed to be 0..num_nodes-1).
    edges : np.ndarray
        Array of shape (m, 2) with undirected edges.
    alive_mask : np.ndarray
        Boolean mask of shape (num_nodes,) indicating currently alive nodes.
    """
    alive = np.asarray(alive_mask, dtype=bool).copy()
    if num_nodes == 0 or not alive.any():
        return alive

    # Union-find over alive nodes only
    parent = np.arange(num_nodes, dtype=int)
    rank = np.zeros(num_nodes, dtype=int)

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx = find(x)
        ry = find(y)
        if rx == ry:
            return
        if rank[rx] < rank[ry]:
            rx, ry = ry, rx
        parent[ry] = rx
        if rank[rx] == rank[ry]:
            rank[rx] += 1

    # Union edges where both endpoints are alive
    if edges.size > 0:
        edges_arr = np.asarray(edges, dtype=int)
        for u, v in edges_arr:
            if alive[u] and alive[v]:
                union(int(u), int(v))

    # Count component sizes over alive nodes
    comp_size: Dict[int, int] = {}
    for i in range(num_nodes):
        if not alive[i]:
            continue
        r = find(int(i))
        comp_size[r] = comp_size.get(r, 0) + 1

    if not comp_size:
        # All nodes were dead or isolated
        return alive

    # Select the root of the largest component
    largest_root = max(comp_size.items(), key=lambda kv: kv[1])[0]

    # Build new mask: alive and in the largest component
    new_alive = np.zeros(num_nodes, dtype=bool)
    for i in range(num_nodes):
        if alive[i] and find(int(i)) == largest_root:
            new_alive[i] = True
    return new_alive


def run_cascade(system: InterdependentSystem, initial_alive_mask: np.ndarray) -> CascadeResult:
    """
    Run cascading failures on an interdependent two-layer system following
    the Buldyrev et al. (2010) algorithm (exact variant).

    Parameters
    ----------
    system : InterdependentSystem
        Interdependent system with two layers A and B and 1:1 dependencies.
    initial_alive_mask : np.ndarray
        Boolean mask of shape (N,) indicating nodes that survive the initial
        percolation (after protection, if any).
    """
    network = system.network
    dependency = system.dependency

    num_nodes = network.num_nodes
    alive0 = np.asarray(initial_alive_mask, dtype=bool)
    if alive0.shape[0] != num_nodes:
        raise ValueError("initial_alive_mask length must match number of nodes.")

    # Layers A and B (assumed to exist for Buldyrev-style systems)
    try:
        layer_a = network.layers["A"]
        layer_b = network.layers["B"]
    except KeyError as exc:
        raise KeyError("InterdependentSystem must have layers 'A' and 'B' for Buldyrev cascades.") from exc

    edges_a = np.asarray(layer_a.edges, dtype=int)
    edges_b = np.asarray(layer_b.edges, dtype=int)

    dep_A_to_B = np.asarray(dependency.dep_A_to_B, dtype=int)
    dep_B_to_A = np.asarray(dependency.dep_B_to_A, dtype=int)
    if dep_A_to_B.shape[0] != num_nodes or dep_B_to_A.shape[0] != num_nodes:
        raise ValueError("Dependency arrays must have length equal to number of nodes.")

    # Initialize alive states on both layers
    alive_A = alive0.copy()
    alive_B = alive0.copy()

    history: Dict[str, Any] = {"alive_A": [], "alive_B": [], "mcgc": []}

    while True:
        prev_A = alive_A.copy()
        prev_B = alive_B.copy()

        # Step 1: A -> B dependency propagation
        # If node A_i stops functioning, node B_{dep_A_to_B[i]} also stops.
        dead_A_indices = np.where(~alive_A)[0]
        if dead_A_indices.size > 0:
            affected_B = dep_A_to_B[dead_A_indices]
            alive_B[affected_B] = False

        # Step 2: keep only the GCC in B layer
        alive_B = keep_largest_component(num_nodes, edges_b, alive_B)

        # Step 3: B -> A dependency propagation
        dead_B_indices = np.where(~alive_B)[0]
        if dead_B_indices.size > 0:
            affected_A = dep_B_to_A[dead_B_indices]
            alive_A[affected_A] = False

        # Step 4: keep only the GCC in A layer
        alive_A = keep_largest_component(num_nodes, edges_a, alive_A)

        # Record history for this iteration
        current_mcgc_mask = alive_A & alive_B
        history["alive_A"].append(int(alive_A.sum()))
        history["alive_B"].append(int(alive_B.sum()))
        history["mcgc"].append(int(current_mcgc_mask.sum()))

        # Convergence check
        if np.array_equal(alive_A, prev_A) and np.array_equal(alive_B, prev_B):
            break

    final_alive_mask = alive_A & alive_B
    m_infty = float(final_alive_mask.sum()) / float(num_nodes) if num_nodes > 0 else 0.0

    return CascadeResult(final_alive_mask=final_alive_mask, m_infty=m_infty, history=history)


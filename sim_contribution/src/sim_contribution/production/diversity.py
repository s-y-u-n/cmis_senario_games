from __future__ import annotations

import numpy as np


def mean_cosine_similarity(vectors: np.ndarray, eps: float = 1e-8) -> float:
    n = vectors.shape[0]
    if n < 2:
        return 0.0
    norms = np.linalg.norm(vectors, axis=1) + eps
    sim_sum = 0.0
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            sim = float(np.dot(vectors[i], vectors[j]) / (norms[i] * norms[j]))
            sim_sum += sim
            count += 1
    return sim_sum / count if count > 0 else 0.0


def diversity_score(vectors: np.ndarray, eps: float = 1e-8) -> float:
    mean_sim = mean_cosine_similarity(vectors, eps=eps)
    return 1.0 - mean_sim

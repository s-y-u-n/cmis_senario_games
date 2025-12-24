from __future__ import annotations

import numpy as np


def add_noise(value: float, rng: np.random.Generator, sigma: float) -> float:
    return float(value + rng.normal(0.0, sigma))

import numpy as np

def rms(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=np.float64)
    return float(np.sqrt(np.mean(x * x))) if len(x) else 0.0

def peak_abs(x: np.ndarray) -> float:
    x = np.asarray(x)
    return float(np.max(np.abs(x))) if len(x) else 0.0

def crest_factor(x: np.ndarray) -> float:
    r = rms(x)
    return peak_abs(x) / r if r > 0 else 0.0

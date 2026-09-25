"""
Metrics storage and statistical analysis utilities.
Tracks operation latencies, counts, min/max/average statistics.
"""

import threading
from typing import Dict, List, Any, Optional

_metrics_lock = threading.Lock()
_metrics_data: Dict[str, List[float]] = {}
_metrics_enabled: bool = True


def set_metrics_enabled(enabled: bool) -> None:
    """Enable or disable metric recording at runtime."""
    global _metrics_enabled
    _metrics_enabled = enabled


def record_metric(name: str, value_ms: float) -> None:
    """Record a latency measurement in milliseconds."""
    if not _metrics_enabled:
        return
    with _metrics_lock:
        if name not in _metrics_data:
            _metrics_data[name] = []
        _metrics_data[name].append(value_ms)
        # Keep bounded history per metric to avoid unbounded memory growth
        if len(_metrics_data[name]) > 1000:
            _metrics_data[name] = _metrics_data[name][-500:]


def get_metrics() -> Dict[str, List[float]]:
    """Return raw recorded metrics dictionary copy."""
    with _metrics_lock:
        return {k: list(v) for k, v in _metrics_data.items()}


def get_metric_stats() -> Dict[str, Dict[str, float]]:
    """
    Return statistical summary of all recorded metrics.
    Includes count, mean, min, max, and p95.
    """
    with _metrics_lock:
        stats: Dict[str, Dict[str, float]] = {}
        for name, values in _metrics_data.items():
            if not values:
                continue
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            p95_idx = int(0.95 * n)
            p95 = sorted_vals[min(p95_idx, n - 1)]
            stats[name] = {
                "count": n,
                "avg_ms": sum(values) / n,
                "min_ms": sorted_vals[0],
                "max_ms": sorted_vals[-1],
                "p95_ms": p95,
            }
        return stats


def clear_metrics() -> None:
    """Reset all recorded metrics."""
    with _metrics_lock:
        _metrics_data.clear()

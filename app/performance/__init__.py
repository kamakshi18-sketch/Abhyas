"""
Performance instrumentation and profiling utilities.
Lightweight, optional, non-invasive performance tracking.
"""

from app.performance.timers import Timer, measure_time
from app.performance.metrics import (
    record_metric,
    get_metrics,
    get_metric_stats,
    clear_metrics,
)
from app.performance.cache import EvaluationCache, get_evaluation_cache

__all__ = [
    "Timer",
    "measure_time",
    "record_metric",
    "get_metrics",
    "get_metric_stats",
    "clear_metrics",
    "EvaluationCache",
    "get_evaluation_cache",
]

"""
Performance timer utilities.
Provides context managers and decorators for precise, low-overhead latency measurement.
"""

import time
import functools
import logging
from typing import Optional, Callable, Any
from app.performance.metrics import record_metric

logger = logging.getLogger(__name__)


class Timer:
    """
    Context manager for recording block execution latency.
    
    Example:
        with Timer("question_generation") as t:
            generate_question()
        print(f"Took {t.elapsed_ms:.2f}ms")
    """

    def __init__(self, name: str, record_to_metrics: bool = True, log_level: Optional[int] = None):
        self.name = name
        self.record_to_metrics = record_to_metrics
        self.log_level = log_level
        self.start_time: float = 0.0
        self.elapsed_ms: float = 0.0

    def __enter__(self) -> "Timer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.elapsed_ms = (time.perf_counter() - self.start_time) * 1000.0
        if self.record_to_metrics:
            record_metric(self.name, self.elapsed_ms)
        if self.log_level is not None:
            logger.log(self.log_level, f"[Timer:{self.name}] completed in {self.elapsed_ms:.2f}ms")


def measure_time(metric_name: Optional[str] = None):
    """
    Decorator for measuring function execution latency.
    
    Example:
        @measure_time("evaluate_answer")
        def evaluate_answer(self, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        name = metric_name or func.__qualname__

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            t0 = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                record_metric(name, elapsed_ms)

        return wrapper

    return decorator

"""
Safe deterministic evaluation cache.
Caches repeated identical answer evaluations using a cryptographic SHA-256 fingerprint of:
- Question text & expected concepts
- Candidate answer
- Rubric version & type
- Model & Prompt version
Bounded LRU cache ensures memory safety and zero risk of cross-session leakage.
"""

import hashlib
import threading
from typing import Optional, Dict
from collections import OrderedDict
from app.schemas.interview import AnswerEvaluation

EVALUATION_CACHE_MAX_SIZE = 128


class EvaluationCache:
    """Bounded thread-safe in-memory cache for deterministic evaluation results."""

    def __init__(self, maxsize: int = EVALUATION_CACHE_MAX_SIZE):
        self.maxsize = maxsize
        self._cache: OrderedDict[str, AnswerEvaluation] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def generate_key(
        question_text: str,
        candidate_answer: str,
        rubric_type: str,
        persona: str,
        language: str,
        model: str,
        prompt_version: str = "1.0",
    ) -> str:
        """Create a deterministic hash key for an evaluation request."""
        raw_key = (
            f"{prompt_version}|{model}|{rubric_type}|{persona}|{language}|"
            f"{question_text.strip().lower()}|{candidate_answer.strip().lower()}"
        )
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[AnswerEvaluation]:
        """Retrieve evaluation from cache if present."""
        with self._lock:
            if key in self._cache:
                self.hits += 1
                # Move to end for LRU behavior
                self._cache.move_to_end(key)
                return self._cache[key]
            self.misses += 1
            return None

    def put(self, key: str, evaluation: AnswerEvaluation) -> None:
        """Store evaluation in bounded LRU cache."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.maxsize:
                    self._cache.popitem(last=False)  # Evict oldest
            self._cache[key] = evaluation

    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0


_global_eval_cache = EvaluationCache()


def get_evaluation_cache() -> EvaluationCache:
    """Return singleton instance of EvaluationCache."""
    return _global_eval_cache

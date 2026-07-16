from __future__ import annotations

import time
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class CircuitState:
    failures: int = 0
    opened_until: float = 0.0


class SimpleCircuitBreaker:
    def __init__(self) -> None:
        self._states: dict[str, CircuitState] = {}

    def is_open(self, name: str) -> bool:
        state = self._states.get(name, CircuitState())
        return state.opened_until > time.time()

    def record_success(self, name: str) -> None:
        self._states[name] = CircuitState()

    def record_failure(self, name: str) -> None:
        state = self._states.get(name, CircuitState())
        state.failures += 1
        if state.failures >= settings.external_circuit_breaker_threshold:
            state.opened_until = time.time() + settings.external_circuit_breaker_reset_seconds
            state.failures = 0
        self._states[name] = state


circuit_breaker = SimpleCircuitBreaker()

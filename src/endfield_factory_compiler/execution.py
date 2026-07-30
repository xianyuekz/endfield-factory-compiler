from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class ExecutionOptions:
    """Cross-stage resource and reproducibility settings.

    The current routing backend is serial, but accepting one shared execution
    contract now prevents future solvers from inventing incompatible thread,
    seed and timeout settings.
    """

    jobs: int = 1
    deterministic: bool = True
    seed: int = 0
    time_limit_seconds: float | None = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.jobs, bool)
            or not isinstance(self.jobs, int)
            or self.jobs < 1
        ):
            raise ValueError("jobs must be a positive integer")
        if not isinstance(self.deterministic, bool):
            raise ValueError("deterministic must be true or false")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        if (
            self.time_limit_seconds is not None
            and (
                isinstance(self.time_limit_seconds, bool)
                or not isinstance(self.time_limit_seconds, (int, float))
                or not isfinite(float(self.time_limit_seconds))
                or self.time_limit_seconds <= 0
            )
        ):
            raise ValueError("time_limit_seconds must be greater than zero")

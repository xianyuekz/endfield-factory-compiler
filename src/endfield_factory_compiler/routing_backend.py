from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .execution import ExecutionOptions
from .model import PlacedDevice, RegionPack, Route, SynthesisResult


@dataclass(frozen=True)
class RoutingProblem:
    pack: RegionPack
    synthesis: SynthesisResult
    devices: list[PlacedDevice]


@dataclass
class RoutingStats:
    backend_name: str
    requested_jobs: int
    effective_jobs: int
    deterministic: bool
    seed: int
    routes_requested: int = 0
    routes_completed: int = 0
    routes_failed: int = 0
    astar_calls: int = 0
    expanded_states: int = 0
    generated_states: int = 0
    heap_pushes: int = 0
    peak_frontier: int = 0
    total_path_length: int = 0
    elapsed_seconds: float = 0.0
    cpu_seconds: float = 0.0
    observed_core_equivalents: float | None = None
    timed_out: bool = False


@dataclass
class RoutingResult:
    routes: list[Route]
    stats: RoutingStats


class RouterBackend(Protocol):
    name: str

    def route(
        self,
        problem: RoutingProblem,
        options: ExecutionOptions,
    ) -> RoutingResult:
        """Route one physical-design problem and return telemetry."""

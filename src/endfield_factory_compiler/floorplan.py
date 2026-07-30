from __future__ import annotations

from dataclasses import dataclass, replace

from .drc import run_drc
from .execution import ExecutionOptions
from .metrics import calculate_metrics
from .model import (
    CompilationMetrics,
    Diagnostic,
    FloorplanSearchOptions,
    FloorplanSearchResult,
    GridSpec,
    LayoutResult,
    PlacedDevice,
    Project,
    Rect,
    RegionPack,
    SynthesisResult,
)
from .placement import PlacementError, place_devices_compact
from .routing import route_design
from .routing_backend import RouterBackend, RoutingResult


class FloorplanSearchError(ValueError):
    """Raised when floorplan search options are invalid."""


@dataclass
class FloorplanCandidate:
    pack: RegionPack
    devices: list[PlacedDevice]
    routing: RoutingResult
    layout: LayoutResult
    metrics: CompilationMetrics
    diagnostics: list[Diagnostic]
    width: int
    height: int
    search: FloorplanSearchResult | None = None

    @property
    def has_errors(self) -> bool:
        return any(item.severity == "error" for item in self.diagnostics)


def _clip_obstacles(pack: RegionPack, width: int, height: int) -> tuple[Rect, ...]:
    clipped = []
    for obstacle in pack.grid.obstacles:
        left = max(0, obstacle.x)
        top = max(0, obstacle.y)
        right = min(width, obstacle.x + obstacle.width)
        bottom = min(height, obstacle.y + obstacle.height)
        if left < right and top < bottom:
            clipped.append(Rect(left, top, right - left, bottom - top))
    return tuple(clipped)


def _with_area(pack: RegionPack, width: int, height: int) -> RegionPack:
    return replace(
        pack,
        grid=GridSpec(
            width=width,
            height=height,
            max_power=pack.grid.max_power,
            obstacles=_clip_obstacles(pack, width, height),
        ),
    )


def evaluate_floorplan(
    project: Project,
    pack: RegionPack,
    synthesis: SynthesisResult,
    devices: list[PlacedDevice],
    options: ExecutionOptions,
    router: RouterBackend | None,
) -> FloorplanCandidate:
    routing = route_design(
        pack,
        synthesis,
        devices,
        options=options,
        backend=router,
    )
    layout = LayoutResult(devices=devices, routes=routing.routes)
    metrics = calculate_metrics(pack, synthesis, layout)
    diagnostics = run_drc(
        project,
        pack,
        synthesis,
        layout,
        metrics,
        routing.stats,
    )
    return FloorplanCandidate(
        pack,
        devices,
        routing,
        layout,
        metrics,
        diagnostics,
        pack.grid.width,
        pack.grid.height,
    )


def _requirements(
    pack: RegionPack,
    synthesis: SynthesisResult,
) -> tuple[int, int, int]:
    device_tiles = 0
    min_width = 0
    min_height = 0
    for node in synthesis.nodes:
        recipe = pack.recipes[node.recipe_id]
        device = pack.devices[recipe.device]
        device_tiles += node.machine_count * device.width * device.height
        min_width = max(min_width, device.width + 2)
        min_height = max(min_height, device.height + 1)
    return max(device_tiles, min_width * min_height), min_width, min_height


def _candidate_dimensions(
    pack: RegionPack,
    *,
    lower_bound_area: int,
    upper_bound_area: int,
    min_width: int,
    min_height: int,
) -> list[tuple[int, int]]:
    dimensions = []
    for width in range(min_width, pack.grid.width + 1):
        max_height = min(pack.grid.height, (upper_bound_area - 1) // width)
        for height in range(min_height, max_height + 1):
            area = width * height
            if area >= lower_bound_area:
                dimensions.append((width, height))
    dimensions.sort(key=lambda item: (item[0] * item[1], item[0] + item[1], item[0]))
    return dimensions


def search_minimum_floorplan(
    project: Project,
    pack: RegionPack,
    synthesis: SynthesisResult,
    baseline: FloorplanCandidate | None,
    *,
    search_options: FloorplanSearchOptions,
    execution_options: ExecutionOptions,
    router: RouterBackend | None,
) -> FloorplanCandidate:
    if search_options.max_candidates <= 0:
        raise FloorplanSearchError("floorplan.max_candidates must be greater than zero")
    if search_options.strategy != "compact-first-fit":
        raise FloorplanSearchError(
            f"Unknown floorplan strategy: {search_options.strategy!r}"
        )

    lower_bound_area, min_width, min_height = _requirements(pack, synthesis)
    baseline_area = (
        max(1, baseline.metrics.bounding_box_area)
        if baseline is not None
        else pack.grid.width * pack.grid.height
    )
    dimensions = _candidate_dimensions(
        pack,
        lower_bound_area=lower_bound_area,
        upper_bound_area=baseline_area,
        min_width=min_width,
        min_height=min_height,
    )
    candidates_tested = 0
    exhausted = True

    for width, height in dimensions:
        if candidates_tested >= search_options.max_candidates:
            exhausted = False
            break
        candidates_tested += 1
        candidate_pack = _with_area(pack, width, height)
        try:
            devices = place_devices_compact(candidate_pack, synthesis)
        except PlacementError:
            continue
        candidate = evaluate_floorplan(
            project,
            candidate_pack,
            synthesis,
            devices,
            execution_options,
            router,
        )
        if not candidate.has_errors:
            candidate.search = FloorplanSearchResult(
                enabled=True,
                strategy=search_options.strategy,
                candidate_budget=search_options.max_candidates,
                lower_bound_area=lower_bound_area,
                baseline_area=baseline_area,
                candidates_tested=candidates_tested,
                feasible=True,
                proven_minimum_for_strategy=True,
                selected_width=width,
                selected_height=height,
                selected_area=width * height,
            )
            return candidate

    if baseline is None:
        raise FloorplanSearchError(
            "No feasible floorplan found within the candidate budget"
        )

    baseline.search = FloorplanSearchResult(
        enabled=True,
        strategy=search_options.strategy,
        candidate_budget=search_options.max_candidates,
        lower_bound_area=lower_bound_area,
        baseline_area=baseline_area,
        candidates_tested=candidates_tested,
        feasible=not baseline.has_errors,
        proven_minimum_for_strategy=exhausted,
        selected_width=baseline.metrics.bounding_box_width,
        selected_height=baseline.metrics.bounding_box_height,
        selected_area=baseline.metrics.bounding_box_area,
    )
    return baseline

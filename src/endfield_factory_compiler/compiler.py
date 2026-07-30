from __future__ import annotations

from dataclasses import dataclass

from .execution import ExecutionOptions
from .floorplan import evaluate_floorplan, search_minimum_floorplan
from .model import (
    CompilationMetrics,
    Diagnostic,
    FloorplanSearchOptions,
    FloorplanSearchResult,
    LayoutResult,
    Project,
    RegionPack,
    SynthesisResult,
    to_dict,
)
from .placement import PlacementError, place_devices
from .routing_backend import RouterBackend, RoutingStats
from .synthesis import synthesize


@dataclass
class CompilationResult:
    project: Project
    pack: RegionPack
    synthesis: SynthesisResult
    layout: LayoutResult
    metrics: CompilationMetrics
    diagnostics: list[Diagnostic]
    execution_options: ExecutionOptions
    routing_stats: RoutingStats
    floorplan_search: FloorplanSearchResult | None = None

    @property
    def has_errors(self) -> bool:
        return any(item.severity == "error" for item in self.diagnostics)

    def to_dict(self) -> dict:
        return {
            "format": "endfield-factory-compiler-plan",
            "format_version": 1,
            "execution": to_dict(self.execution_options),
            "project": {
                "name": self.project.name,
                "targets": dict(self.project.targets),
                "constraints": to_dict(self.project.constraints),
            },
            "region": {
                "id": self.pack.id,
                "name": self.pack.name,
                "version": self.pack.version,
            },
            "synthesis": to_dict(self.synthesis),
            "layout": to_dict(self.layout),
            "metrics": to_dict(self.metrics),
            "routing_stats": to_dict(self.routing_stats),
            "floorplan_search": to_dict(self.floorplan_search),
            "diagnostics": to_dict(self.diagnostics),
        }


def compile_project(
    project: Project,
    pack: RegionPack,
    *,
    options: ExecutionOptions | None = None,
    floorplan: FloorplanSearchOptions | None = None,
    router: RouterBackend | None = None,
) -> CompilationResult:
    selected_options = options or ExecutionOptions()
    floorplan_options = floorplan or FloorplanSearchOptions()
    synthesis = synthesize(pack, project.targets)
    baseline = None
    if not floorplan_options.enabled:
        devices = place_devices(pack, synthesis)
        baseline = evaluate_floorplan(
            project,
            pack,
            synthesis,
            devices,
            selected_options,
            router,
        )
        selected = baseline
    else:
        try:
            devices = place_devices(pack, synthesis)
            baseline = evaluate_floorplan(
                project,
                pack,
                synthesis,
                devices,
                selected_options,
                router,
            )
        except PlacementError:
            baseline = None
        selected = search_minimum_floorplan(
            project,
            pack,
            synthesis,
            baseline,
            search_options=floorplan_options,
            execution_options=selected_options,
            router=router,
        )
    assert selected is not None
    return CompilationResult(
        project=project,
        pack=selected.pack,
        synthesis=synthesis,
        layout=selected.layout,
        metrics=selected.metrics,
        diagnostics=selected.diagnostics,
        execution_options=selected_options,
        routing_stats=selected.routing.stats,
        floorplan_search=selected.search,
    )

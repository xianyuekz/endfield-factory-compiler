from __future__ import annotations

from dataclasses import dataclass

from .drc import run_drc
from .execution import ExecutionOptions
from .metrics import calculate_metrics
from .model import (
    CompilationMetrics,
    Diagnostic,
    LayoutResult,
    Project,
    RegionPack,
    SynthesisResult,
    to_dict,
)
from .placement import place_devices
from .routing import route_design
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
            "diagnostics": to_dict(self.diagnostics),
        }


def compile_project(
    project: Project,
    pack: RegionPack,
    *,
    options: ExecutionOptions | None = None,
    router: RouterBackend | None = None,
) -> CompilationResult:
    selected_options = options or ExecutionOptions()
    synthesis = synthesize(pack, project.targets)
    devices = place_devices(pack, synthesis)
    routing = route_design(
        pack,
        synthesis,
        devices,
        options=selected_options,
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
    return CompilationResult(
        project=project,
        pack=pack,
        synthesis=synthesis,
        layout=layout,
        metrics=metrics,
        diagnostics=diagnostics,
        execution_options=selected_options,
        routing_stats=routing.stats,
    )

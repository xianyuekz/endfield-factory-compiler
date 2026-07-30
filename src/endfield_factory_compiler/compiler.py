from __future__ import annotations

from dataclasses import dataclass

from .drc import run_drc
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
from .routing import route_logistics
from .synthesis import synthesize


@dataclass
class CompilationResult:
    project: Project
    pack: RegionPack
    synthesis: SynthesisResult
    layout: LayoutResult
    metrics: CompilationMetrics
    diagnostics: list[Diagnostic]

    @property
    def has_errors(self) -> bool:
        return any(item.severity == "error" for item in self.diagnostics)

    def to_dict(self) -> dict:
        return {
            "format": "endfield-factory-compiler-plan",
            "format_version": 1,
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
            "diagnostics": to_dict(self.diagnostics),
        }


def compile_project(project: Project, pack: RegionPack) -> CompilationResult:
    synthesis = synthesize(pack, project.targets)
    devices = place_devices(pack, synthesis)
    routes = route_logistics(pack, synthesis, devices)
    layout = LayoutResult(devices=devices, routes=routes)
    metrics = calculate_metrics(pack, synthesis, layout)
    diagnostics = run_drc(project, pack, synthesis, layout, metrics)
    return CompilationResult(
        project=project,
        pack=pack,
        synthesis=synthesis,
        layout=layout,
        metrics=metrics,
        diagnostics=diagnostics,
    )

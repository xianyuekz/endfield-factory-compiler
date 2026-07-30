from __future__ import annotations

from dataclasses import dataclass

from .drc import run_drc
from .model import (
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
            },
            "region": {
                "id": self.pack.id,
                "name": self.pack.name,
                "version": self.pack.version,
            },
            "synthesis": to_dict(self.synthesis),
            "layout": to_dict(self.layout),
            "diagnostics": to_dict(self.diagnostics),
        }


def compile_project(project: Project, pack: RegionPack) -> CompilationResult:
    synthesis = synthesize(pack, project.targets)
    devices = place_devices(pack, synthesis)
    routes = route_logistics(pack, synthesis, devices)
    layout = LayoutResult(devices=devices, routes=routes)
    diagnostics = run_drc(pack, synthesis, layout)
    return CompilationResult(
        project=project,
        pack=pack,
        synthesis=synthesis,
        layout=layout,
        diagnostics=diagnostics,
    )

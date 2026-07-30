from __future__ import annotations

from collections import defaultdict

from .model import (
    Diagnostic,
    LayoutResult,
    RegionPack,
    SynthesisResult,
)


def run_drc(
    pack: RegionPack,
    synthesis: SynthesisResult,
    layout: LayoutResult,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    if synthesis.total_power > pack.grid.max_power:
        diagnostics.append(
            Diagnostic(
                "error",
                "POWER_BUDGET_EXCEEDED",
                f"Required power {synthesis.total_power:.1f} exceeds "
                f"region budget {pack.grid.max_power:.1f}.",
            )
        )
    else:
        diagnostics.append(
            Diagnostic(
                "info",
                "POWER_BUDGET_OK",
                f"Power usage is {synthesis.total_power:.1f} / "
                f"{pack.grid.max_power:.1f}.",
            )
        )

    occupied: dict[tuple[int, int], str] = {}
    obstacle_cells = set().union(*(rect.cells() for rect in pack.grid.obstacles))
    for device in layout.devices:
        rect = device.rect
        if (
            rect.x < 0
            or rect.y < 0
            or rect.x + rect.width > pack.grid.width
            or rect.y + rect.height > pack.grid.height
        ):
            diagnostics.append(
                Diagnostic(
                    "error",
                    "DEVICE_OUT_OF_BOUNDS",
                    f"{device.id} is outside the buildable grid.",
                )
            )
        for cell in rect.cells():
            if cell in obstacle_cells:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        "DEVICE_ON_OBSTACLE",
                        f"{device.id} overlaps obstacle at {cell}.",
                    )
                )
            if cell in occupied:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        "DEVICE_OVERLAP",
                        f"{device.id} overlaps {occupied[cell]} at {cell}.",
                    )
                )
            occupied[cell] = device.id

    route_cells: dict[tuple[int, int], set[str]] = defaultdict(set)
    for route in layout.routes:
        if not route.routed:
            diagnostics.append(
                Diagnostic(
                    "error",
                    "ROUTE_FAILED",
                    f"No path for {route.item} from {route.source} to {route.sink}.",
                )
            )
            continue
        if route.required_rate > route.capacity + 1e-9:
            diagnostics.append(
                Diagnostic(
                    "error",
                    "ROUTE_CAPACITY_EXCEEDED",
                    f"{route.id} carries {route.required_rate:.2f}/min, above "
                    f"its {route.capacity:.2f}/min capacity.",
                )
            )
        for point in route.points:
            if point in occupied:
                diagnostics.append(
                    Diagnostic(
                        "error",
                        "ROUTE_THROUGH_DEVICE",
                        f"{route.id} crosses {occupied[point]} at {point}.",
                    )
                )
            route_cells[point].add(route.item)

    crossing_count = 0
    for point, items in route_cells.items():
        if len(items) > 1 and not pack.logistics.allow_crossings:
            diagnostics.append(
                Diagnostic(
                    "error",
                    "ROUTE_ITEM_COLLISION",
                    f"Incompatible logistics overlap at {point}: "
                    + ", ".join(sorted(items)),
                )
            )
        elif len(items) > 1:
            crossing_count += 1
    if crossing_count:
        diagnostics.append(
            Diagnostic(
                "info",
                "ROUTE_CROSSINGS",
                f"{crossing_count} logistics crossing(s) use the region's "
                "abstract bridge capability.",
            )
        )

    for node in synthesis.nodes:
        if node.capacity_rate + 1e-9 < node.required_rate:
            diagnostics.append(
                Diagnostic(
                    "error",
                    "PRODUCTION_CAPACITY_SHORTFALL",
                    f"{node.recipe_id} supplies {node.capacity_rate:.2f}/min "
                    f"but needs {node.required_rate:.2f}/min.",
                )
            )

    error_count = sum(diagnostic.severity == "error" for diagnostic in diagnostics)
    warning_count = sum(
        diagnostic.severity == "warning" for diagnostic in diagnostics
    )
    diagnostics.append(
        Diagnostic(
            "info",
            "DRC_SUMMARY",
            f"DRC completed with {error_count} error(s) and "
            f"{warning_count} warning(s).",
        )
    )
    return diagnostics

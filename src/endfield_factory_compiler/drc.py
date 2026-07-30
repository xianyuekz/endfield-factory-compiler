from __future__ import annotations

from collections import defaultdict

from .model import (
    CompilationMetrics,
    Diagnostic,
    LayoutResult,
    PlacedDevice,
    Project,
    RegionPack,
    SynthesisResult,
)


def run_drc(
    project: Project,
    pack: RegionPack,
    synthesis: SynthesisResult,
    layout: LayoutResult,
    metrics: CompilationMetrics,
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

    constraints = project.constraints
    if (
        constraints.max_power is not None
        and synthesis.total_power > constraints.max_power
    ):
        diagnostics.append(
            Diagnostic(
                "error",
                "PROJECT_POWER_CONSTRAINT_EXCEEDED",
                f"Required power {synthesis.total_power:.1f} exceeds project "
                f"constraint {constraints.max_power:.1f}.",
            )
        )
    if (
        constraints.max_devices is not None
        and metrics.device_count > constraints.max_devices
    ):
        diagnostics.append(
            Diagnostic(
                "error",
                "PROJECT_DEVICE_CONSTRAINT_EXCEEDED",
                f"Layout uses {metrics.device_count} devices, above project "
                f"constraint {constraints.max_devices}.",
            )
        )
    if (
        constraints.max_route_tiles is not None
        and metrics.route_tiles > constraints.max_route_tiles
    ):
        diagnostics.append(
            Diagnostic(
                "error",
                "PROJECT_ROUTE_CONSTRAINT_EXCEEDED",
                f"Layout uses {metrics.route_tiles} route tiles, above project "
                f"constraint {constraints.max_route_tiles}.",
            )
        )
    if metrics.area_utilization_percent > 85.0:
        diagnostics.append(
            Diagnostic(
                "warning",
                "HIGH_AREA_UTILIZATION",
                f"Layout uses {metrics.area_utilization_percent:.1f}% of "
                "buildable tiles; later routing changes may be difficult.",
            )
        )

    devices_by_id = {device.id: device for device in layout.devices}
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
    outgoing_rates: dict[str, float] = defaultdict(float)
    incoming_rates: dict[tuple[str, str], float] = defaultdict(float)
    for route in layout.routes:
        incoming_rates[(route.sink, route.item)] += route.required_rate
        if route.source in devices_by_id:
            outgoing_rates[route.source] += route.required_rate
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

    for device_id, assigned_rate in outgoing_rates.items():
        device = devices_by_id[device_id]
        capacity = pack.recipes[device.recipe_id].output_rate_per_minute
        if assigned_rate > capacity + 1e-9:
            diagnostics.append(
                Diagnostic(
                    "error",
                    "PRODUCER_CAPACITY_EXCEEDED",
                    f"{device_id} is assigned {assigned_rate:.2f}/min but can "
                    f"produce only {capacity:.2f}/min.",
                )
            )

    consumers_by_recipe: dict[str, list[PlacedDevice]] = defaultdict(list)
    for device in layout.devices:
        consumers_by_recipe[device.recipe_id].append(device)
    for node in synthesis.nodes:
        consumers = consumers_by_recipe[node.recipe_id]
        for consumer in consumers:
            for item, total_rate in node.input_rates.items():
                expected_rate = total_rate / len(consumers)
                actual_rate = incoming_rates[(consumer.id, item)]
                if abs(actual_rate - expected_rate) > 1e-9:
                    diagnostics.append(
                        Diagnostic(
                            "error",
                            "CONSUMER_INPUT_RATE_MISMATCH",
                            f"{consumer.id} receives {actual_rate:.2f}/min of "
                            f"{item} but needs {expected_rate:.2f}/min.",
                        )
                    )

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

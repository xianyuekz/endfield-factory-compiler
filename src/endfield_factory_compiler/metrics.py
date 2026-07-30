from __future__ import annotations

from collections import defaultdict

from .model import CompilationMetrics, LayoutResult, RegionPack, SynthesisResult


def _route_bends(points: list[tuple[int, int]]) -> int:
    bends = 0
    previous_direction: tuple[int, int] | None = None
    for start, end in zip(points, points[1:]):
        direction = (end[0] - start[0], end[1] - start[1])
        if previous_direction is not None and direction != previous_direction:
            bends += 1
        previous_direction = direction
    return bends


def calculate_metrics(
    pack: RegionPack,
    synthesis: SynthesisResult,
    layout: LayoutResult,
) -> CompilationMetrics:
    obstacle_cells = set().union(*(rect.cells() for rect in pack.grid.obstacles))
    device_cells = set().union(*(device.rect.cells() for device in layout.devices))
    route_cells: set[tuple[int, int]] = set()
    route_items: dict[tuple[int, int], set[str]] = defaultdict(set)
    for route in layout.routes:
        route_cells.update(route.points)
        for point in route.points:
            route_items[point].add(route.item)

    buildable_tiles = pack.grid.width * pack.grid.height - len(obstacle_cells)
    used_tiles = len((device_cells | route_cells) - obstacle_cells)
    bounded_cells = (device_cells | route_cells) - obstacle_cells
    if bounded_cells:
        min_x = min(x for x, _ in bounded_cells)
        max_x = max(x for x, _ in bounded_cells)
        min_y = min(y for _, y in bounded_cells)
        max_y = max(y for _, y in bounded_cells)
        bounding_box_width = max_x - min_x + 1
        bounding_box_height = max_y - min_y + 1
        bounding_box_area = bounding_box_width * bounding_box_height
    else:
        bounding_box_width = 0
        bounding_box_height = 0
        bounding_box_area = 0
    bounding_box_utilization = (
        100.0 * used_tiles / bounding_box_area if bounding_box_area else 0.0
    )
    utilization = 100.0 * used_tiles / buildable_tiles if buildable_tiles else 0.0
    power_utilization = (
        100.0 * synthesis.total_power / pack.grid.max_power
        if pack.grid.max_power
        else 0.0
    )
    return CompilationMetrics(
        device_count=len(layout.devices),
        device_tiles=len(device_cells),
        route_count=len(layout.routes),
        route_tiles=len(route_cells),
        total_route_length=sum(route.length for route in layout.routes),
        route_bends=sum(_route_bends(route.points) for route in layout.routes),
        crossing_tiles=sum(len(items) > 1 for items in route_items.values()),
        buildable_tiles=buildable_tiles,
        used_tiles=used_tiles,
        bounding_box_width=bounding_box_width,
        bounding_box_height=bounding_box_height,
        bounding_box_area=bounding_box_area,
        bounding_box_utilization_percent=bounding_box_utilization,
        area_utilization_percent=utilization,
        power_utilization_percent=power_utilization,
        raw_input_rate_per_minute=sum(synthesis.source_rates.values()),
    )

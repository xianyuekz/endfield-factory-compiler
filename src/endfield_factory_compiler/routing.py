from __future__ import annotations

import heapq
from collections import defaultdict
from itertools import count

from .model import PlacedDevice, RegionPack, Route, SynthesisResult


def _neighbors(
    point: tuple[int, int], width: int, height: int
) -> tuple[tuple[int, int], ...]:
    x, y = point
    return tuple(
        candidate
        for candidate in ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1))
        if 0 <= candidate[0] < width and 0 <= candidate[1] < height
    )


def _astar(
    start: tuple[int, int],
    goal: tuple[int, int],
    width: int,
    height: int,
    blocked: set[tuple[int, int]],
) -> list[tuple[int, int]]:
    if start in blocked or goal in blocked:
        return []
    serial = count()
    frontier: list[tuple[int, int, tuple[int, int]]] = [
        (0, next(serial), start)
    ]
    came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    cost: dict[tuple[int, int], int] = {start: 0}

    while frontier:
        _, _, current = heapq.heappop(frontier)
        if current == goal:
            path = []
            cursor: tuple[int, int] | None = current
            while cursor is not None:
                path.append(cursor)
                cursor = came_from[cursor]
            return list(reversed(path))
        for neighbor in _neighbors(current, width, height):
            if neighbor in blocked:
                continue
            new_cost = cost[current] + 1
            if neighbor not in cost or new_cost < cost[neighbor]:
                cost[neighbor] = new_cost
                priority = new_cost + abs(goal[0] - neighbor[0]) + abs(
                    goal[1] - neighbor[1]
                )
                heapq.heappush(
                    frontier, (priority, next(serial), neighbor)
                )
                came_from[neighbor] = current
    return []


def _boundary_port(
    preferred_y: int,
    pack: RegionPack,
    blocked: set[tuple[int, int]],
) -> tuple[int, int] | None:
    candidates = sorted(
        range(pack.grid.height),
        key=lambda y: (abs(y - preferred_y), y),
    )
    for y in candidates:
        point = (0, y)
        if point not in blocked:
            return point
    return None


def route_logistics(
    pack: RegionPack,
    synthesis: SynthesisResult,
    devices: list[PlacedDevice],
) -> list[Route]:
    device_cells = set().union(*(device.rect.cells() for device in devices))
    obstacle_cells = set().union(*(rect.cells() for rect in pack.grid.obstacles))
    hard_blocked = device_cells | obstacle_cells
    route_occupancy: dict[tuple[int, int], str] = {}
    producers: dict[str, list[PlacedDevice]] = defaultdict(list)
    consumers_by_recipe: dict[str, list[PlacedDevice]] = defaultdict(list)
    for device in devices:
        producers[device.output_item].append(device)
        consumers_by_recipe[device.recipe_id].append(device)

    routes: list[Route] = []
    producer_cursor: dict[str, int] = defaultdict(int)
    route_number = 1

    for node in synthesis.nodes:
        consumers = consumers_by_recipe[node.recipe_id]
        for consumer in consumers:
            for item, total_input_rate in node.input_rates.items():
                sink = consumer.input_port(item)
                required_rate = total_input_rate / len(consumers)
                item_producers = producers.get(item, [])
                if item_producers:
                    source_device = item_producers[
                        producer_cursor[item] % len(item_producers)
                    ]
                    producer_cursor[item] += 1
                    source = source_device.output_port()
                    source_name = source_device.id
                else:
                    route_blocked = set(hard_blocked)
                    if not pack.logistics.allow_crossings:
                        route_blocked |= {
                            point
                            for point, occupied_item in route_occupancy.items()
                            if occupied_item != item
                        }
                    boundary = _boundary_port(sink[1], pack, route_blocked)
                    if boundary is None:
                        source = (-1, -1)
                    else:
                        source = boundary
                    source_name = f"external:{item}"

                blocked = set(hard_blocked)
                if not pack.logistics.allow_crossings:
                    blocked |= {
                        point
                        for point, occupied_item in route_occupancy.items()
                        if occupied_item != item
                    }
                blocked.discard(source)
                blocked.discard(sink)
                points = (
                    _astar(
                        source,
                        sink,
                        pack.grid.width,
                        pack.grid.height,
                        blocked,
                    )
                    if source[0] >= 0
                    else []
                )
                if points:
                    for point in points:
                        route_occupancy.setdefault(point, item)
                routes.append(
                    Route(
                        id=f"route-{route_number}",
                        item=item,
                        source=source_name,
                        sink=consumer.id,
                        required_rate=required_rate,
                        capacity=pack.logistics.tile_capacity_per_minute,
                        points=points,
                    )
                )
                route_number += 1
    return routes

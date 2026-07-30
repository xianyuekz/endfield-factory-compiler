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
    route_occupancy: dict[tuple[int, int], set[str]],
    item: str,
    allow_crossings: bool,
    crossing_penalty: float,
    bend_penalty: float,
) -> list[tuple[int, int]]:
    if start in blocked or goal in blocked:
        return []
    serial = count()
    start_state = (start, None)
    frontier: list[
        tuple[float, int, tuple[tuple[int, int], tuple[int, int] | None]]
    ] = [(0.0, next(serial), start_state)]
    came_from: dict[
        tuple[tuple[int, int], tuple[int, int] | None],
        tuple[tuple[int, int], tuple[int, int] | None] | None,
    ] = {start_state: None}
    cost: dict[
        tuple[tuple[int, int], tuple[int, int] | None], float
    ] = {start_state: 0.0}

    while frontier:
        _, _, current_state = heapq.heappop(frontier)
        current, previous_direction = current_state
        if current == goal:
            path: list[tuple[int, int]] = []
            cursor = current_state
            while cursor is not None:
                path.append(cursor[0])
                cursor = came_from[cursor]
            return list(reversed(path))
        for neighbor in _neighbors(current, width, height):
            if neighbor in blocked:
                continue
            direction = (neighbor[0] - current[0], neighbor[1] - current[1])
            occupied_items = route_occupancy.get(neighbor, set())
            different_items = occupied_items - {item}
            if different_items and not allow_crossings:
                continue

            step_cost = 1.0
            if item in occupied_items and not different_items:
                step_cost = 0.65
            if different_items:
                step_cost += crossing_penalty
            if (
                previous_direction is not None
                and direction != previous_direction
            ):
                step_cost += bend_penalty

            neighbor_state = (neighbor, direction)
            new_cost = cost[current_state] + step_cost
            if (
                neighbor_state not in cost
                or new_cost < cost[neighbor_state]
            ):
                cost[neighbor_state] = new_cost
                heuristic = 0.65 * (
                    abs(goal[0] - neighbor[0]) + abs(goal[1] - neighbor[1])
                )
                heapq.heappush(
                    frontier,
                    (new_cost + heuristic, next(serial), neighbor_state),
                )
                came_from[neighbor_state] = current_state
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
    route_occupancy: dict[tuple[int, int], set[str]] = defaultdict(set)
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
                            for point, occupied_items in route_occupancy.items()
                            if occupied_items - {item}
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
                        for point, occupied_items in route_occupancy.items()
                        if occupied_items - {item}
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
                        route_occupancy,
                        item,
                        pack.logistics.allow_crossings,
                        pack.logistics.crossing_penalty,
                        pack.logistics.bend_penalty,
                    )
                    if source[0] >= 0
                    else []
                )
                if points:
                    for point in points:
                        route_occupancy[point].add(item)
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

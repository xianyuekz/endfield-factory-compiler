from __future__ import annotations

import heapq
from collections import defaultdict
from dataclasses import dataclass
from itertools import count
from time import perf_counter, process_time

from .execution import ExecutionOptions
from .model import PlacedDevice, RegionPack, Route, SynthesisResult
from .routing_backend import (
    RouterBackend,
    RoutingProblem,
    RoutingResult,
    RoutingStats,
)


@dataclass
class _SearchResult:
    points: list[tuple[int, int]]
    expanded_states: int
    generated_states: int
    heap_pushes: int
    peak_frontier: int
    timed_out: bool = False


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
    deadline: float | None,
) -> _SearchResult:
    if start in blocked or goal in blocked:
        return _SearchResult([], 0, 0, 0, 0)
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
    expanded_states = 0
    generated_states = 1
    heap_pushes = 1
    peak_frontier = 1

    while frontier:
        if (
            deadline is not None
            and expanded_states % 256 == 0
            and perf_counter() >= deadline
        ):
            return _SearchResult(
                [],
                expanded_states,
                generated_states,
                heap_pushes,
                peak_frontier,
                timed_out=True,
            )
        _, _, current_state = heapq.heappop(frontier)
        expanded_states += 1
        current, previous_direction = current_state
        if current == goal:
            path: list[tuple[int, int]] = []
            cursor = current_state
            while cursor is not None:
                path.append(cursor[0])
                cursor = came_from[cursor]
            return _SearchResult(
                list(reversed(path)),
                expanded_states,
                generated_states,
                heap_pushes,
                peak_frontier,
            )
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
                generated_states += 1
                heap_pushes += 1
                peak_frontier = max(peak_frontier, len(frontier))
                came_from[neighbor_state] = current_state
    return _SearchResult(
        [],
        expanded_states,
        generated_states,
        heap_pushes,
        peak_frontier,
    )


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


def _route_serial(
    pack: RegionPack,
    synthesis: SynthesisResult,
    devices: list[PlacedDevice],
    options: ExecutionOptions,
) -> RoutingResult:
    started_at = perf_counter()
    cpu_started_at = process_time()
    deadline = (
        started_at + options.time_limit_seconds
        if options.time_limit_seconds is not None
        else None
    )
    stats = RoutingStats(
        backend_name=GridAStarRouter.name,
        requested_jobs=options.jobs,
        effective_jobs=1,
        deterministic=True,
        seed=options.seed,
    )
    device_cells = set().union(*(device.rect.cells() for device in devices))
    obstacle_cells = set().union(*(rect.cells() for rect in pack.grid.obstacles))
    hard_blocked = device_cells | obstacle_cells
    route_occupancy: dict[tuple[int, int], set[str]] = defaultdict(set)
    producers: dict[str, list[PlacedDevice]] = defaultdict(list)
    consumers_by_recipe: dict[str, list[PlacedDevice]] = defaultdict(list)
    producer_remaining: dict[str, float] = {}
    for device in devices:
        producers[device.output_item].append(device)
        consumers_by_recipe[device.recipe_id].append(device)
        producer_remaining[device.id] = pack.recipes[
            device.recipe_id
        ].output_rate_per_minute

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
                allocations: list[
                    tuple[PlacedDevice | None, str, float]
                ] = []
                if not item_producers:
                    allocations.append((None, f"external:{item}", required_rate))
                else:
                    remaining_demand = required_rate
                    while remaining_demand > 1e-9:
                        while (
                            producer_cursor[item] < len(item_producers)
                            and producer_remaining[
                                item_producers[producer_cursor[item]].id
                            ]
                            <= 1e-9
                        ):
                            producer_cursor[item] += 1
                        if producer_cursor[item] >= len(item_producers):
                            allocations.append(
                                (
                                    None,
                                    f"unallocated:{item}",
                                    remaining_demand,
                                )
                            )
                            break
                        source_device = item_producers[producer_cursor[item]]
                        allocation = min(
                            remaining_demand,
                            producer_remaining[source_device.id],
                        )
                        allocations.append(
                            (source_device, source_device.id, allocation)
                        )
                        producer_remaining[source_device.id] -= allocation
                        remaining_demand -= allocation

                for source_device, source_name, allocated_rate in allocations:
                    route_blocked = set(hard_blocked)
                    if not pack.logistics.allow_crossings:
                        route_blocked |= {
                            point
                            for point, occupied_items in route_occupancy.items()
                            if occupied_items - {item}
                        }
                    if source_device is not None:
                        source = source_device.output_port()
                    elif source_name.startswith("external:"):
                        boundary = _boundary_port(
                            sink[1], pack, route_blocked
                        )
                        source = boundary if boundary is not None else (-1, -1)
                    else:
                        source = (-1, -1)

                    blocked = set(route_blocked)
                    blocked.discard(source)
                    blocked.discard(sink)
                    search_result = (
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
                            deadline,
                        )
                        if source[0] >= 0
                        else _SearchResult([], 0, 0, 0, 0)
                    )
                    if source[0] >= 0:
                        stats.astar_calls += 1
                    stats.expanded_states += search_result.expanded_states
                    stats.generated_states += search_result.generated_states
                    stats.heap_pushes += search_result.heap_pushes
                    stats.peak_frontier = max(
                        stats.peak_frontier,
                        search_result.peak_frontier,
                    )
                    stats.timed_out = (
                        stats.timed_out or search_result.timed_out
                    )
                    points = search_result.points
                    if points:
                        for point in points:
                            route_occupancy[point].add(item)
                    routes.append(
                        Route(
                            id=f"route-{route_number}",
                            item=item,
                            source=source_name,
                            sink=consumer.id,
                            required_rate=allocated_rate,
                            capacity=pack.logistics.tile_capacity_per_minute,
                            points=points,
                        )
                    )
                    route_number += 1
    stats.routes_requested = len(routes)
    stats.routes_completed = sum(route.routed for route in routes)
    stats.routes_failed = stats.routes_requested - stats.routes_completed
    stats.total_path_length = sum(route.length for route in routes)
    stats.elapsed_seconds = perf_counter() - started_at
    stats.cpu_seconds = process_time() - cpu_started_at
    if stats.elapsed_seconds >= 0.05:
        stats.observed_core_equivalents = (
            stats.cpu_seconds / stats.elapsed_seconds
        )
    return RoutingResult(routes=routes, stats=stats)


class GridAStarRouter:
    """Deterministic serial reference backend for grid-based routing."""

    name = "serial-grid-astar"

    def route(
        self,
        problem: RoutingProblem,
        options: ExecutionOptions,
    ) -> RoutingResult:
        return _route_serial(
            problem.pack,
            problem.synthesis,
            problem.devices,
            options,
        )


DEFAULT_ROUTER = GridAStarRouter()


def route_design(
    pack: RegionPack,
    synthesis: SynthesisResult,
    devices: list[PlacedDevice],
    *,
    options: ExecutionOptions | None = None,
    backend: RouterBackend | None = None,
) -> RoutingResult:
    problem = RoutingProblem(pack=pack, synthesis=synthesis, devices=devices)
    selected_options = options or ExecutionOptions()
    selected_backend = backend or DEFAULT_ROUTER
    return selected_backend.route(problem, selected_options)


def route_logistics(
    pack: RegionPack,
    synthesis: SynthesisResult,
    devices: list[PlacedDevice],
) -> list[Route]:
    """Compatibility wrapper returning only routes from the default backend."""
    return route_design(pack, synthesis, devices).routes

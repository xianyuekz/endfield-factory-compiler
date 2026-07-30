from __future__ import annotations

import heapq
from collections import defaultdict
from dataclasses import dataclass
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
    cell_ids: list[int]
    expanded_states: int
    generated_states: int
    heap_pushes: int
    peak_frontier: int
    timed_out: bool = False


_DIRECTIONS = ((1, 0), (0, 1), (-1, 0), (0, -1))
_NO_DIRECTION = 4


def _cell_id(point: tuple[int, int], width: int) -> int:
    return point[1] * width + point[0]


def _maybe_cell_id(
    point: tuple[int, int],
    width: int,
    height: int,
) -> int | None:
    if 0 <= point[0] < width and 0 <= point[1] < height:
        return _cell_id(point, width)
    return None


def _cell_point(cell_id: int, width: int) -> tuple[int, int]:
    return cell_id % width, cell_id // width


@dataclass
class _AStarWorkspace:
    width: int
    height: int
    came_from: list[int]
    cost: list[float]
    seen: list[int]
    closed: list[int]
    epoch: int = 0

    @classmethod
    def create(cls, width: int, height: int) -> _AStarWorkspace:
        state_count = width * height * 5
        return cls(
            width=width,
            height=height,
            came_from=[-1] * state_count,
            cost=[0.0] * state_count,
            seen=[0] * state_count,
            closed=[0] * state_count,
        )

    def next_epoch(self) -> int:
        self.epoch += 1
        return self.epoch


def _astar(
    start: int,
    goal: int,
    width: int,
    height: int,
    blocked: set[int],
    route_occupancy: dict[int, set[str]],
    item: str,
    allow_crossings: bool,
    crossing_penalty: float,
    bend_penalty: float,
    deadline: float | None,
    workspace: _AStarWorkspace,
) -> _SearchResult:
    if start in blocked or goal in blocked:
        return _SearchResult([], 0, 0, 0, 0)

    epoch = workspace.next_epoch()
    start_state = start * 5 + _NO_DIRECTION
    goal_x, goal_y = _cell_point(goal, width)
    frontier: list[tuple[float, int, int]] = [(0.0, 0, start_state)]
    serial = 1
    workspace.came_from[start_state] = -1
    workspace.cost[start_state] = 0.0
    workspace.seen[start_state] = epoch
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
        if workspace.closed[current_state] == epoch:
            continue
        workspace.closed[current_state] = epoch
        expanded_states += 1
        current = current_state // 5
        previous_direction = current_state % 5
        if current == goal:
            path: list[int] = []
            cursor = current_state
            while cursor != -1:
                path.append(cursor // 5)
                cursor = workspace.came_from[cursor]
            return _SearchResult(
                list(reversed(path)),
                expanded_states,
                generated_states,
                heap_pushes,
                peak_frontier,
            )
        x, y = _cell_point(current, width)
        for direction, (dx, dy) in enumerate(_DIRECTIONS):
            neighbor_x = x + dx
            neighbor_y = y + dy
            if not (0 <= neighbor_x < width and 0 <= neighbor_y < height):
                continue
            neighbor = neighbor_y * width + neighbor_x
            if neighbor in blocked:
                continue
            occupied_items = route_occupancy.get(neighbor)
            has_same_item = (
                occupied_items is not None and item in occupied_items
            )
            has_different_items = (
                occupied_items is not None
                and any(occupied_item != item for occupied_item in occupied_items)
            )
            if has_different_items and not allow_crossings:
                continue

            step_cost = 1.0
            if has_same_item and not has_different_items:
                step_cost = 0.65
            if has_different_items:
                step_cost += crossing_penalty
            if (
                previous_direction != _NO_DIRECTION
                and direction != previous_direction
            ):
                step_cost += bend_penalty

            neighbor_state = neighbor * 5 + direction
            new_cost = workspace.cost[current_state] + step_cost
            if (
                workspace.seen[neighbor_state] != epoch
                or new_cost < workspace.cost[neighbor_state]
            ):
                workspace.seen[neighbor_state] = epoch
                workspace.cost[neighbor_state] = new_cost
                heuristic = 0.65 * (
                    abs(goal_x - neighbor_x) + abs(goal_y - neighbor_y)
                )
                heapq.heappush(
                    frontier,
                    (new_cost + heuristic, serial, neighbor_state),
                )
                serial += 1
                generated_states += 1
                heap_pushes += 1
                peak_frontier = max(peak_frontier, len(frontier))
                workspace.came_from[neighbor_state] = current_state
    return _SearchResult(
        [],
        expanded_states,
        generated_states,
        heap_pushes,
        peak_frontier,
    )


def _boundary_port(
    preferred_y: int,
    width: int,
    height: int,
    blocked: set[int],
) -> int | None:
    candidates = sorted(
        range(height),
        key=lambda y: (abs(y - preferred_y), y),
    )
    for y in candidates:
        cell_id = y * width
        if cell_id not in blocked:
            return cell_id
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
    width = pack.grid.width
    height = pack.grid.height
    astar_workspace = _AStarWorkspace.create(width, height)
    device_cells = {
        _cell_id(cell, width)
        for device in devices
        for cell in device.rect.cells()
    }
    obstacle_cells = {
        _cell_id(cell, width)
        for rect in pack.grid.obstacles
        for cell in rect.cells()
    }
    hard_blocked = device_cells | obstacle_cells
    route_occupancy: dict[int, set[str]] = defaultdict(set)
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
                sink_point = consumer.input_port(item)
                sink = _maybe_cell_id(sink_point, width, height)
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
                        source_point = source_device.output_port()
                        source = _maybe_cell_id(
                            source_point,
                            width,
                            height,
                        )
                    elif source_name.startswith("external:"):
                        boundary = _boundary_port(
                            sink_point[1],
                            width,
                            height,
                            route_blocked,
                        )
                        source = boundary
                    else:
                        source = None

                    blocked = set(route_blocked)
                    if source is not None:
                        blocked.discard(source)
                    if sink is not None:
                        blocked.discard(sink)
                    search_result = (
                        _astar(
                            source,
                            sink,
                            width,
                            height,
                            blocked,
                            route_occupancy,
                            item,
                            pack.logistics.allow_crossings,
                            pack.logistics.crossing_penalty,
                            pack.logistics.bend_penalty,
                            deadline,
                            astar_workspace,
                        )
                        if source is not None and sink is not None
                        else _SearchResult([], 0, 0, 0, 0)
                    )
                    if source is not None and sink is not None:
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
                    if search_result.cell_ids:
                        for cell_id in search_result.cell_ids:
                            route_occupancy[cell_id].add(item)
                    points = [
                        _cell_point(cell_id, width)
                        for cell_id in search_result.cell_ids
                    ]
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

    name = "serial-compact-grid-astar"

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

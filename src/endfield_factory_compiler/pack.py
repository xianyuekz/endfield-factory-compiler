from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import (
    DeviceSpec,
    GridSpec,
    LogisticsSpec,
    Project,
    ProjectConstraints,
    RecipeSpec,
    Rect,
    RegionPack,
)


class PackError(ValueError):
    """Raised when a region pack or project is invalid."""


def _read_json(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError as exc:
        raise PackError(f"File not found: {source}") from exc
    except json.JSONDecodeError as exc:
        raise PackError(f"Invalid JSON in {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise PackError(f"Top-level JSON value must be an object: {source}")
    return value


def _positive(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise PackError(f"{label} must be a number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise PackError(f"{label} must be a number") from exc
    if number <= 0:
        raise PackError(f"{label} must be greater than zero")
    return number


def _nonnegative(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise PackError(f"{label} must be a number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise PackError(f"{label} must be a number") from exc
    if number < 0:
        raise PackError(f"{label} must be zero or greater")
    return number


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise PackError(f"{label} must be true or false")
    return value


def _optional_positive(value: Any, label: str) -> float | None:
    return None if value is None else _positive(value, label)


def _optional_positive_int(value: Any, label: str) -> int | None:
    if value is None:
        return None
    number = _positive(value, label)
    if not number.is_integer():
        raise PackError(f"{label} must be a whole number")
    return int(number)


def _positive_int(value: Any, label: str) -> int:
    number = _positive(value, label)
    if not number.is_integer():
        raise PackError(f"{label} must be a whole number")
    return int(number)


def _nonnegative_int(value: Any, label: str) -> int:
    number = _nonnegative(value, label)
    if not number.is_integer():
        raise PackError(f"{label} must be a whole number")
    return int(number)


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PackError(f"{label} must be an object")
    return value


def _array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise PackError(f"{label} must be an array")
    return value


def load_region_pack(path: str | Path) -> RegionPack:
    data = _read_json(path)
    if data.get("schema_version") != 1:
        raise PackError("Only region-pack schema_version 1 is supported")

    grid_data = _object(data.get("grid", {}), "grid")
    obstacle_data = _array(grid_data.get("obstacles", []), "grid.obstacles")
    obstacles_list: list[Rect] = []
    for index, value in enumerate(obstacle_data):
        rect = _object(value, f"grid.obstacles[{index}]")
        obstacles_list.append(
            Rect(
                _nonnegative_int(rect.get("x"), f"grid.obstacles[{index}].x"),
                _nonnegative_int(rect.get("y"), f"grid.obstacles[{index}].y"),
                _positive_int(
                    rect.get("width"), f"grid.obstacles[{index}].width"
                ),
                _positive_int(
                    rect.get("height"), f"grid.obstacles[{index}].height"
                ),
            )
        )
    obstacles = tuple(obstacles_list)
    grid = GridSpec(
        width=_positive_int(grid_data.get("width"), "grid.width"),
        height=_positive_int(grid_data.get("height"), "grid.height"),
        max_power=_positive(grid_data.get("max_power"), "grid.max_power"),
        obstacles=obstacles,
    )

    logistics_data = _object(data.get("logistics", {}), "logistics")
    logistics = LogisticsSpec(
        tile_capacity_per_minute=_positive(
            logistics_data.get("tile_capacity_per_minute"),
            "logistics.tile_capacity_per_minute",
        ),
        allow_crossings=_boolean(
            logistics_data.get("allow_crossings", False),
            "logistics.allow_crossings",
        ),
        crossing_penalty=_nonnegative(
            logistics_data.get("crossing_penalty", 8.0),
            "logistics.crossing_penalty",
        ),
        bend_penalty=_nonnegative(
            logistics_data.get("bend_penalty", 0.4),
            "logistics.bend_penalty",
        ),
    )

    items_data = _object(data.get("items", {}), "items")
    items: dict[str, str] = {}
    for item_id, value in items_data.items():
        item_data = _object(value, f"items.{item_id}")
        items[str(item_id)] = str(item_data.get("name", item_id))
    if not items:
        raise PackError("A region pack must define at least one item")

    devices: dict[str, DeviceSpec] = {}
    devices_data = _object(data.get("devices", {}), "devices")
    for device_id, value in devices_data.items():
        device_data = _object(value, f"devices.{device_id}")
        devices[device_id] = DeviceSpec(
            id=device_id,
            name=str(device_data.get("name", device_id)),
            width=_positive_int(
                device_data.get("width"), f"devices.{device_id}.width"
            ),
            height=_positive_int(
                device_data.get("height"), f"devices.{device_id}.height"
            ),
            power=_positive(device_data.get("power"), f"devices.{device_id}.power"),
        )
    if not devices:
        raise PackError("A region pack must define at least one device")

    recipes: dict[str, RecipeSpec] = {}
    outputs: set[str] = set()
    recipes_data = _object(data.get("recipes", {}), "recipes")
    for recipe_id, value in recipes_data.items():
        recipe_data = _object(value, f"recipes.{recipe_id}")
        device_id = str(recipe_data.get("device"))
        if device_id not in devices:
            raise PackError(
                f"Recipe {recipe_id!r} references unknown device {device_id!r}"
            )
        output_data = _object(
            recipe_data.get("output", {}), f"recipes.{recipe_id}.output"
        )
        output_item = str(output_data.get("item"))
        if output_item not in items:
            raise PackError(
                f"Recipe {recipe_id!r} produces unknown item {output_item!r}"
            )
        if output_item in outputs:
            raise PackError(
                f"Multiple recipes produce {output_item!r}; schema v1 requires one"
            )
        outputs.add(output_item)
        inputs_data = _object(
            recipe_data.get("inputs", {}), f"recipes.{recipe_id}.inputs"
        )
        inputs = {
            str(item): _positive(
                amount, f"recipes.{recipe_id}.inputs.{item}"
            )
            for item, amount in inputs_data.items()
        }
        unknown_inputs = set(inputs) - set(items)
        if unknown_inputs:
            raise PackError(
                f"Recipe {recipe_id!r} has unknown inputs: "
                + ", ".join(sorted(unknown_inputs))
            )
        recipes[recipe_id] = RecipeSpec(
            id=recipe_id,
            name=str(recipe_data.get("name", recipe_id)),
            device=device_id,
            cycle_seconds=_positive(
                recipe_data.get("cycle_seconds"),
                f"recipes.{recipe_id}.cycle_seconds",
            ),
            inputs=inputs,
            output_item=output_item,
            output_amount=_positive(
                output_data.get("amount"),
                f"recipes.{recipe_id}.output.amount",
            ),
        )
    if not recipes:
        raise PackError("A region pack must define at least one recipe")

    for obstacle in obstacles:
        if (
            obstacle.x < 0
            or obstacle.y < 0
            or obstacle.x + obstacle.width > grid.width
            or obstacle.y + obstacle.height > grid.height
        ):
            raise PackError(f"Obstacle is outside the grid: {obstacle}")

    return RegionPack(
        schema_version=1,
        id=str(data.get("id", "unknown")),
        name=str(data.get("name", data.get("id", "Unknown region"))),
        version=str(data.get("version", "0.0.0")),
        grid=grid,
        logistics=logistics,
        items=items,
        devices=devices,
        recipes=recipes,
    )


def load_project(path: str | Path) -> Project:
    source = Path(path)
    data = _read_json(source)
    if data.get("schema_version") != 1:
        raise PackError("Only project schema_version 1 is supported")
    targets_data = _object(data.get("targets", {}), "targets")
    targets = {
        str(item): _positive(rate, f"targets.{item}")
        for item, rate in targets_data.items()
    }
    if not targets:
        raise PackError("A project must define at least one target")
    region_pack = data.get("region_pack")
    if not isinstance(region_pack, str) or not region_pack.strip():
        raise PackError("project.region_pack must be a path")
    constraints_data = _object(data.get("constraints", {}), "project.constraints")
    constraints = ProjectConstraints(
        max_power=_optional_positive(
            constraints_data.get("max_power"), "constraints.max_power"
        ),
        max_devices=_optional_positive_int(
            constraints_data.get("max_devices"), "constraints.max_devices"
        ),
        max_route_tiles=_optional_positive_int(
            constraints_data.get("max_route_tiles"), "constraints.max_route_tiles"
        ),
    )
    resolved_pack = (source.parent / region_pack).resolve()
    return Project(
        schema_version=1,
        name=str(data.get("name", source.stem)),
        region_pack_path=str(resolved_pack),
        targets=targets,
        constraints=constraints,
    )

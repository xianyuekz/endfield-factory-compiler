from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import (
    DeviceSpec,
    GridSpec,
    LogisticsSpec,
    Project,
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
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise PackError(f"{label} must be a number") from exc
    if number <= 0:
        raise PackError(f"{label} must be greater than zero")
    return number


def load_region_pack(path: str | Path) -> RegionPack:
    data = _read_json(path)
    if data.get("schema_version") != 1:
        raise PackError("Only region-pack schema_version 1 is supported")

    grid_data = data.get("grid", {})
    obstacles = tuple(
        Rect(
            int(rect["x"]),
            int(rect["y"]),
            int(rect["width"]),
            int(rect["height"]),
        )
        for rect in grid_data.get("obstacles", [])
    )
    grid = GridSpec(
        width=int(_positive(grid_data.get("width"), "grid.width")),
        height=int(_positive(grid_data.get("height"), "grid.height")),
        max_power=_positive(grid_data.get("max_power"), "grid.max_power"),
        obstacles=obstacles,
    )

    logistics_data = data.get("logistics", {})
    logistics = LogisticsSpec(
        tile_capacity_per_minute=_positive(
            logistics_data.get("tile_capacity_per_minute"),
            "logistics.tile_capacity_per_minute",
        ),
        allow_crossings=bool(logistics_data.get("allow_crossings", False)),
    )

    items = {
        str(item_id): str(item_data.get("name", item_id))
        for item_id, item_data in data.get("items", {}).items()
    }
    if not items:
        raise PackError("A region pack must define at least one item")

    devices: dict[str, DeviceSpec] = {}
    for device_id, device_data in data.get("devices", {}).items():
        devices[device_id] = DeviceSpec(
            id=device_id,
            name=str(device_data.get("name", device_id)),
            width=int(_positive(device_data.get("width"), f"devices.{device_id}.width")),
            height=int(
                _positive(device_data.get("height"), f"devices.{device_id}.height")
            ),
            power=_positive(device_data.get("power"), f"devices.{device_id}.power"),
        )
    if not devices:
        raise PackError("A region pack must define at least one device")

    recipes: dict[str, RecipeSpec] = {}
    outputs: set[str] = set()
    for recipe_id, recipe_data in data.get("recipes", {}).items():
        device_id = str(recipe_data.get("device"))
        if device_id not in devices:
            raise PackError(
                f"Recipe {recipe_id!r} references unknown device {device_id!r}"
            )
        output_data = recipe_data.get("output", {})
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
        inputs = {
            str(item): _positive(
                amount, f"recipes.{recipe_id}.inputs.{item}"
            )
            for item, amount in recipe_data.get("inputs", {}).items()
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
    targets = {
        str(item): _positive(rate, f"targets.{item}")
        for item, rate in data.get("targets", {}).items()
    }
    if not targets:
        raise PackError("A project must define at least one target")
    region_pack = data.get("region_pack")
    if not isinstance(region_pack, str) or not region_pack.strip():
        raise PackError("project.region_pack must be a path")
    resolved_pack = (source.parent / region_pack).resolve()
    return Project(
        schema_version=1,
        name=str(data.get("name", source.stem)),
        region_pack_path=str(resolved_pack),
        targets=targets,
    )

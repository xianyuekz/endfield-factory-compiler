from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    def cells(self) -> set[tuple[int, int]]:
        return {
            (x, y)
            for x in range(self.x, self.x + self.width)
            for y in range(self.y, self.y + self.height)
        }


@dataclass(frozen=True)
class GridSpec:
    width: int
    height: int
    max_power: float
    obstacles: tuple[Rect, ...] = ()


@dataclass(frozen=True)
class DeviceSpec:
    id: str
    name: str
    width: int
    height: int
    power: float


@dataclass(frozen=True)
class RecipeSpec:
    id: str
    name: str
    device: str
    cycle_seconds: float
    inputs: dict[str, float]
    output_item: str
    output_amount: float

    @property
    def output_rate_per_minute(self) -> float:
        return self.output_amount * 60.0 / self.cycle_seconds


@dataclass(frozen=True)
class LogisticsSpec:
    tile_capacity_per_minute: float
    allow_crossings: bool = False


@dataclass(frozen=True)
class RegionPack:
    schema_version: int
    id: str
    name: str
    version: str
    grid: GridSpec
    logistics: LogisticsSpec
    items: dict[str, str]
    devices: dict[str, DeviceSpec]
    recipes: dict[str, RecipeSpec]

    def recipe_by_output(self) -> dict[str, RecipeSpec]:
        return {recipe.output_item: recipe for recipe in self.recipes.values()}


@dataclass(frozen=True)
class Project:
    schema_version: int
    name: str
    region_pack_path: str
    targets: dict[str, float]


@dataclass
class SynthesisNode:
    recipe_id: str
    item: str
    required_rate: float
    machine_count: int
    capacity_rate: float
    depth: int
    input_rates: dict[str, float]
    power: float


@dataclass
class SynthesisResult:
    targets: dict[str, float]
    nodes: list[SynthesisNode]
    source_rates: dict[str, float]
    total_power: float


@dataclass
class PlacedDevice:
    id: str
    recipe_id: str
    device_id: str
    output_item: str
    depth: int
    rect: Rect
    input_items: tuple[str, ...]

    def input_port(self, item: str) -> tuple[int, int]:
        try:
            index = self.input_items.index(item)
        except ValueError:
            index = 0
        offset = min(index, self.rect.height - 1)
        return self.rect.x - 1, self.rect.y + offset

    def output_port(self) -> tuple[int, int]:
        return (
            self.rect.x + self.rect.width,
            self.rect.y + self.rect.height // 2,
        )


@dataclass
class Route:
    id: str
    item: str
    source: str
    sink: str
    required_rate: float
    capacity: float
    points: list[tuple[int, int]]

    @property
    def routed(self) -> bool:
        return bool(self.points)


@dataclass
class LayoutResult:
    devices: list[PlacedDevice]
    routes: list[Route]


@dataclass
class Diagnostic:
    severity: str
    code: str
    message: str


def to_dict(value: Any) -> Any:
    """Convert nested dataclasses and tuples into JSON-friendly values."""
    if hasattr(value, "__dataclass_fields__"):
        return {key: to_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: to_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_dict(item) for item in value]
    return value

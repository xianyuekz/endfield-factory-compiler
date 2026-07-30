# Region-pack format

A region pack is the compiler equivalent of an FPGA device-support package. It
describes the available grid, devices, recipes and logistics capabilities.

Schema version 1 uses one JSON file:

```json
{
  "schema_version": 1,
  "id": "my-region",
  "name": "My Region",
  "version": "1.0.0",
  "grid": {
    "width": 64,
    "height": 34,
    "max_power": 600,
    "obstacles": [
      {"x": 10, "y": 12, "width": 3, "height": 4}
    ]
  },
  "logistics": {
    "tile_capacity_per_minute": 60,
    "allow_crossings": false,
    "crossing_penalty": 8,
    "bend_penalty": 0.4
  },
  "items": {
    "ore": {"name": "Ore"},
    "plate": {"name": "Plate"}
  },
  "devices": {
    "smelter": {
      "name": "Smelter",
      "width": 3,
      "height": 3,
      "power": 12
    }
  },
  "recipes": {
    "make_plate": {
      "name": "Plate",
      "device": "smelter",
      "cycle_seconds": 4,
      "inputs": {"ore": 2},
      "output": {"item": "plate", "amount": 1}
    }
  }
}
```

Rates in project files and output plans are expressed per minute. Dimensions
and coordinates use abstract grid tiles. Device input ports are assigned along
the left edge; the output port is centered on the right edge.

`allow_crossings` means the router may model two different logistics items on
one tile as an abstract bridge/underpass. Packs should enable it only when the
target region has an equivalent capability.

`tile_capacity_per_minute` limits both an individual route and the aggregate
same-item flow on any shared logistics trunk tile. Schema-v1 inferred
source/sink cells are treated as ports rather than ordinary trunk tiles because
explicit port capacity is not modeled yet.

`crossing_penalty` controls how strongly the router avoids such abstract
bridges. `bend_penalty` favors simpler paths with fewer turns. Both values must
be zero or greater and are routing costs rather than physical rates.

## Versioning

- `schema_version` describes the file format and is currently `1`.
- `version` describes the data-pack revision and should use semantic
  versioning.
- Use a new pack version when balance updates change recipes or footprints.
- Keep historical releases available when possible so old projects remain
  reproducible.

## Version 1 restrictions

- exactly one recipe may produce a given item;
- recipes must form a directed acyclic graph;
- one recipe has one output item;
- all logistics share one per-tile capacity;
- device ports are inferred rather than declared.

These restrictions are expected to change in later schemas. Please propose
schema changes before adding incompatible fields.

## Data contributions

Submit only data that contributors are allowed to redistribute. Cite public
sources in the pull-request description, and do not commit extracted textures,
icons, audio, proprietary map files or other copyrighted assets.

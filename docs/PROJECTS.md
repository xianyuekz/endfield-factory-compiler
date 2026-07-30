# Project format

A project declares production targets and points to one installed or local
region pack. All rates are measured per minute.

```json
{
  "$schema": "../schemas/project.schema.json",
  "schema_version": 1,
  "name": "8 Control Cores per Minute",
  "region_pack": "../region-packs/demo-valley/region.json",
  "targets": {
    "control_core": 8
  },
  "constraints": {
    "max_power": 400,
    "max_devices": 16,
    "max_route_tiles": 240
  }
}
```

`region_pack` is resolved relative to the project file, which keeps checked-in
examples portable.

## Targets

Each key is an item ID from the region pack. The value is the required output
rate per minute. Multiple targets may share upstream production stages.

## Constraints

All constraints are optional:

- `max_power` limits total device power;
- `max_devices` limits placed device instances;
- `max_route_tiles` limits the number of unique grid tiles touched by routes.

An exceeded constraint is a DRC error and makes `efc compile` return a non-zero
exit status. Region-level limits still apply even when no project constraint is
set.

## Editor support

The checked-in `$schema` field enables validation and autocomplete in editors
that support JSON Schema. The canonical schemas are:

- [`schemas/project.schema.json`](../schemas/project.schema.json)
- [`schemas/region-pack.schema.json`](../schemas/region-pack.schema.json)

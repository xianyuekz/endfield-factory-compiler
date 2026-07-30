# HC Valley Battery Example

This example is the first end-to-end target that resembles a real Arknights:
Endfield factory goal rather than a fictional toy item.

```bash
efc compile examples/hc-valley-battery.json \
  --out build/hc-valley-battery \
  --min-area
```

The compiler will emit:

- `plan.json` with synthesis, placement, routed paths and DRC diagnostics;
- `layout.svg` for visual inspection;
- `report.md` for a readable production summary.

The checked-in snapshot is regenerated with the same command and lives under
[`docs/assets/hc-valley-battery`](assets/hc-valley-battery):

- 28 placed devices;
- 43 routed logistics edges;
- 280 unique route tiles;
- 41 x 17 routed bounding box;
- 697 selected floorplan tiles;
- 604 power in the research pack;
- 0 DRC errors.

## Scope

The target is `6 HC Valley Batteries per minute`, which corresponds to one
full-speed packaging recipe in the current community-data model:

```text
Steel Part x10 + Dense Originium Powder x15
  -> HC Valley Battery x1
```

The upstream chains model Sandleaf Powder, Dense Originium Powder and Steel
Parts. The current compiler still does not generate official in-game blueprint
codes. It generates an inspectable physical plan that can later feed a blueprint
adapter when the format is documented and permitted to support.

The research pack keeps source links beside the data in
[`region-packs/valley-iv-research`](../region-packs/valley-iv-research). Treat
those values as community research data, not an official export.

## Minimum-area mode

`--min-area` turns on deterministic floorplan search. For this project, the
default readable placement has a 61 x 60 routed bounding box. The current
compact first-fit strategy proves that 41 x 17 is the smallest feasible
rectangle it can route under schema-v1 rules.

This is a practical EDA-style acceptance target: changes to placement, routing
or DRC should not silently regress this example back into a loose flowchart.
It is still not a claim of global optimality across future rotations, explicit
ports, splitter devices, multiple logistics tiers or human-designed modules.

## Current Limitations

- no by-products;
- no fluids;
- no depot bus or item-filter objects;
- no thermal-bank consumption model;
- inferred device ports rather than game-accurate rotated ports;
- compact first-fit floorplanning rather than human-style modules or a global
  optimizer.

These are now concrete blockers rather than abstract roadmap items, because the
HC Valley Battery example exercises a large multi-branch recipe chain.

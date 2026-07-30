# Floorplanning and minimum-area search

`efc compile` normally uses a readable depth-column placement. That mode is
useful for explaining a production graph, but it is not a serious attempt to
minimize occupied area.

Use `--min-area` when the goal is a compact physical design:

```bash
efc compile examples/hc-valley-battery.json \
  --out build/hc-valley-battery \
  --min-area \
  --profile balanced
```

Use `--profile low-power` for older machines, `--profile balanced` for the
default acceptance target or `--profile quality` when you want to spend more
time exploring candidate rectangles. `--floorplan-max-candidates N` still
overrides the profile budget explicitly.

The current floorplanner is deterministic and deliberately conservative:

1. synthesize the production graph and machine counts;
2. build the default routed layout as an upper bound;
3. compute a hard lower bound from device footprint area;
4. enumerate candidate rectangles from smaller area to larger area;
5. compact-place devices inside each rectangle with obstacle avoidance;
6. run the real A* router and DRC for that rectangle;
7. select the first candidate with no DRC errors.

Because candidates are tested in area order, a successful result is the minimum
area for the current strategy and model. It is not a mathematical global
optimum across all possible device rotations, port assignments, bus devices,
splitters or negotiated-congestion routing choices.

The search result is written to `plan.json` as `floorplan_search` and reported
in Markdown:

```json
{
  "enabled": true,
  "strategy": "compact-first-fit",
  "candidate_budget": 1000,
  "lower_bound_area": 391,
  "baseline_area": 3660,
  "candidates_tested": 815,
  "feasible": true,
  "proven_minimum_for_strategy": true,
  "selected_width": 41,
  "selected_height": 17,
  "selected_area": 697
}
```

## Throughput correctness

The router tracks per-tile item loads while routing. A route may reuse a tile
only when the same item's aggregate load remains below the region pack's
`logistics.tile_capacity_per_minute`.

DRC repeats the same aggregate-capacity check, so alternate routers cannot
silently accept an overloaded trunk. Schema-v1 inferred source/sink cells are
treated as device or external ports rather than ordinary logistics trunk tiles;
explicit port capacity should become part of a future schema.

## Current limitations

- candidate rectangles are anchored at the region origin;
- devices are not rotated;
- inferred ports are not game-accurate;
- bus/filter/splitter devices are not modeled;
- the objective is minimum rectangle area, not minimum route length;
- high area utilization may be reported as a warning even when the layout is
  intentionally compact.

The intended next step is to make placement and routing pluggable in the same
style as `RouterBackend`, so community contributors can add skyline packers,
simulated annealing, CP-SAT/MILP legalization or PathFinder-style negotiated
congestion without changing project files.

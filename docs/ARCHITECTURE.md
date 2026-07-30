# Architecture

Endfield Factory Compiler intentionally follows a compiler pipeline. Each stage
has a small data contract and can later be replaced independently.

```text
project.json             region.json
     │                       │
     └──────┬────────────────┘
            ▼
      recipe synthesis
            │  logical production graph
            ▼
      technology mapping
            │  concrete device counts
            ▼
        placement
            │  device rectangles + ports
            ▼
         routing
            │  item paths
            ▼
           DRC
            │
            ├── plan.json
            ├── layout.svg
            └── report.md
```

## Modules

- `pack.py` parses and validates project and region-pack inputs.
- `execution.py` owns cross-backend resource and reproducibility settings.
- `synthesis.py` expands target rates into a DAG and maps recipes to devices.
- `placement.py` performs deterministic, obstacle-aware column placement.
- `floorplan.py` performs optional minimum-area rectangle search using compact
  placement, routing and DRC as the feasibility oracle.
- `routing.py` splits flow across producer capacity, then connects device ports
  using grid-based A*.
- `routing_backend.py` defines the replaceable backend and telemetry contracts.
- `metrics.py` measures physical area, route length, bends and crossings.
- `drc.py` checks physical and throughput constraints.
- `render.py` produces a standalone SVG report.
- `report.py` produces a deterministic, reviewable Markdown report.
- `compiler.py` owns the pipeline and stable result object.
- `cli.py` is a thin shell over the library API.
- `native/route_core` is a Rust prototype for routing hot loops that will
  eventually sit behind the same `RouterBackend` contract.

The Python package remains dependency-free. Its compact A* router prices
congestion, incompatible crossings and bends while remaining deterministic.
Native, CP-SAT, MILP, PathFinder or annealing-style backends should be optional
and should consume/produce the same intermediate models.

All backends receive `ExecutionOptions`; no stage may create an unbudgeted
nested worker pool. See [the performance guide](PERFORMANCE.md).
Major architectural choices are tracked in [ADRs](adr), starting with
[ADR 0001](adr/0001-native-routing-core.md).

## Design principles

### Data is not code

Game- and region-specific values belong in versioned region packs. The core
must remain useful with fictional data and must not require extracted assets.

### Determinism first

The same project and region pack should produce byte-for-byte stable plans
where practical. This makes regression testing and community review easier.

### Inspectable intermediate results

`plan.json` contains synthesis nodes, placed rectangles, routed points and
diagnostics. A GUI should read this file rather than importing private
implementation details.

### Backends are replaceable

The baseline algorithms favor clarity over optimality. More advanced work can
add:

- MILP/CP-SAT recipe selection and machine allocation
- standard-cell or module-based placement
- exact/heuristic floorplanning with rotations and explicit ports
- analytical global placement followed by legalization
- negotiated-congestion routing
- tick-based throughput simulation

## Blueprint adapters

Official blueprint-code support is not assumed. If a documented and permitted
format becomes available, implement it as an adapter from `plan.json`.
The physical-design pipeline must remain usable without that adapter.

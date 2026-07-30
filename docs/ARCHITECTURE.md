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
- `synthesis.py` expands target rates into a DAG and maps recipes to devices.
- `placement.py` performs deterministic, obstacle-aware column placement.
- `routing.py` connects device ports using grid-based A*.
- `metrics.py` measures physical area, route length, bends and crossings.
- `drc.py` checks physical and throughput constraints.
- `render.py` produces a standalone SVG report.
- `report.py` produces a deterministic, reviewable Markdown report.
- `compiler.py` owns the pipeline and stable result object.
- `cli.py` is a thin shell over the library API.

The current implementation is deliberately dependency-free. Its A* router
prices congestion, incompatible crossings and bends while remaining
deterministic. A future CP-SAT, MILP or PathFinder backend should be optional
and should consume/produce the same intermediate models.

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
- analytical global placement followed by legalization
- negotiated-congestion routing
- tick-based throughput simulation

## Blueprint adapters

Official blueprint-code support is not assumed. If a documented and permitted
format becomes available, implement it as an adapter from `plan.json`.
The physical-design pipeline must remain usable without that adapter.

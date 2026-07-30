# ADR 0002: Low-end friendly native-first architecture

## Status

Accepted.

## Context

Endfield factory planning is a fan tool use case, not a workstation-only EDA
use case. Many users will run it on ordinary laptops or older desktops while
also running a game client, browser and chat tools.

The prototype is written mostly in Python because Python is excellent for a
small open-source seed project: it keeps schemas, CLI behavior, reports and
tests easy to inspect and modify. That does not make Python an acceptable
long-term home for placement, routing, DRC or floorplan-search hot loops.

The `--min-area` flow makes the issue visible: one compile may evaluate
hundreds of candidate rectangles, and each candidate can invoke placement,
routing and DRC. A naive implementation can easily become unusable on low-end
hardware.

## Decision

Keep Python as the control plane and treat performance-sensitive algorithms as
native kernel candidates.

Python owns:

- project and region-pack loading;
- schema validation and friendly errors;
- CLI/profile selection;
- orchestration between backends;
- JSON, SVG and Markdown reports;
- deterministic reference tests.

Native kernels own, or should eventually own:

- route search;
- placement legalization;
- floorplan candidate evaluation;
- congestion repair;
- DRC over occupancy/load arrays;
- parallel scheduling of independent candidates or nets.

Rust is the preferred first native language for kernels because it offers
predictable memory layout, safe parallelism and a clean path to Python
bindings. C or C++ remain acceptable when a third-party solver requires them.

The default CLI profile must stay usable on modest machines. More expensive
search should be opt-in through explicit quality profiles or explicit budgets.

## Consequences

- Python implementations are reference backends, not the target performance
  endpoint.
- Every hot loop must expose deterministic telemetry before being replaced.
- Backend APIs must accept one shared resource contract rather than creating
  hidden thread pools.
- Low-power users should be able to cap search effort without editing project
  files.
- CI should keep at least one compact real-ish target small enough to run
  routinely.

The immediate implementation is a CLI `--profile` preset system. It controls
floorplan search effort today and gives future native kernels a stable place
to read low-power/balanced/quality intent.

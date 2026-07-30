# ADR 0001: Native Route Core

## Status

Accepted.

## Context

Routing is the current physical-design hotspot. The Python implementation is
useful as a deterministic reference, but pure Python object churn is not the
right long-term shape for large grids, multi-net routing or multi-core search.

The project still needs a low-friction Python CLI for region packs, reports,
schemas and community experimentation. Requiring every user to compile native
extensions before the native API is stable would make the project harder to
try.

## Decision

Keep Python as the orchestration layer and introduce a standalone Rust route
core under `native/route_core`.

The Rust core starts as an independently tested crate. It is not part of the
Python wheel yet. The first kernel is deterministic single-net A* using:

- integer cell ids instead of `(x, y)` tuples;
- integer state ids for direction-aware routing;
- reusable workspace arrays;
- per-cell occupancy bitsets.

## Consequences

The repository now has two quality tracks:

- Python tests protect the public CLI, data model and reports.
- Rust `fmt`, `clippy` and tests protect the native hot path.

The next milestone is a Python `RouterBackend` wrapper around the Rust core,
with the current Python router retained as the fallback and reference oracle.

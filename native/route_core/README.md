# Native Route Core

This crate is the first native hot-path target for Endfield Factory Compiler.
It is intentionally independent from the Python package for now, so users can
still install and run `efc` without a Rust toolchain.

The current kernel provides deterministic single-net A* over compact integer
cell/state arrays with per-cell occupancy bitsets. The next integration step is
to expose this through a Python binding and then batch routes with
deterministic conflict handling.

```bash
cargo test --manifest-path native/route_core/Cargo.toml
```

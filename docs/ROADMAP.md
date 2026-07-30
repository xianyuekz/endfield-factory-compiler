# Correctness roadmap

This roadmap orders work by whether the compiler can incorrectly accept an
unbuildable plan. It is intentionally narrower than a feature wish list.

## P0 — correctness blockers

- [x] Split physical flow across producer devices and check per-device input
  and output rates (`v0.2.1`).
- [ ] Accumulate same-item flow on shared route tiles and reject aggregate
  throughput above tile capacity.

## P1 — physical-model gaps

- [ ] Replace inferred side ports with explicit typed ports, facing and device
  rotation rules.
- [ ] Model multiple logistics technologies instead of one global tile
  capacity and an abstract crossing flag.
- [ ] Feed routing failures and congestion back into placement instead of using
  a one-way pipeline.
- [ ] Add an install/list/resolve workflow for versioned region packs.

## P2 — synthesis-model gaps

- [ ] Support alternate recipes with an explicit optimization objective.
- [ ] Support by-products and multi-output recipes.
- [ ] Support permitted cyclic production graphs with a steady-state solver.
- [ ] Add tick-based simulation to verify buffers and transient throughput.

## P3 — adoption gaps

- [ ] Add a community-maintained, legally redistributable real-data pack.
- [ ] Add a local visual project editor without introducing an online service.
- [ ] Add a blueprint adapter only if a documented and permitted format becomes
  available.

Each item should start with a failing regression test or a minimal reproducible
project. A clean DRC report must mean that every implemented physical rule is
actually satisfied.

## Performance foundation

- [x] Add a shared execution budget, replaceable router interface and routing
  telemetry (`v0.3.0`).
- [ ] Replace tuple/dictionary-heavy A* state with compact integer-indexed
  storage.
- [ ] Add deterministic multi-start process parallelism.
- [ ] Add conflict-batched parallel routing with deterministic commit and
  negotiated-congestion repair.

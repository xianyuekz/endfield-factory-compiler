# Performance and parallelism

## Current baseline

The reference router is deterministic and serial. On a 24-core Windows machine,
the fictional demo compiled in roughly 10 ms and routing accounted for about
95% of CPU time.

Synthetic scaling measurements showed the risk:

| Devices | Routes | Routing time |
| ---: | ---: | ---: |
| 13 | 25 | 7–10 ms |
| 90 | 190 | 0.22 s |
| 179 | 381 | 0.68 s |
| 267 | 558 | 1.45 s |
| 357 | 763 | 2.58 s |

These numbers are machine-specific. The important signal is that routing grew
much faster than device count while process CPU time stayed close to wall time,
which means one logical core was active.

Run the checked-in benchmark to establish a local baseline:

```bash
python benchmarks/compile_scaling.py --repeats 3
```

After the `v0.3.1` compact-state router change, the same audit machine measured:

| Target rate | Devices | Routes | Routing time |
| ---: | ---: | ---: | ---: |
| 8/min | 13 | 25 | 4.8 ms |
| 32/min | 46 | 96 | 59.9 ms |
| 64/min | 90 | 190 | 172.2 ms |

This is still single-core execution. The win comes from avoiding tuple-heavy
search state and reusing A* workspace arrays across routes.

## Execution contract

`ExecutionOptions` is the single CPU and reproducibility contract shared by
compiler backends:

```python
ExecutionOptions(
    jobs=8,
    deterministic=True,
    seed=0,
    time_limit_seconds=30,
)
```

The current `GridAStarRouter` uses compact integer state arrays, but remains
intentionally honest: it reports
`effective_jobs=1`. Requesting more jobs produces a DRC warning instead of
silently pretending to use multiple cores.

`RoutingStats` records:

- requested and effective jobs;
- route and A* call counts;
- expanded and generated states;
- heap pushes and peak frontier size;
- total path length and elapsed time;
- process CPU time and observed core equivalents for sufficiently long runs;
- timeout status.

Every `plan.json` and Markdown report contains this telemetry.

## Floorplan search cost

`efc compile --min-area` is a higher-level optimization loop. It tests candidate
rectangles in area order and uses placement, routing and DRC as the feasibility
oracle. This makes the result meaningful, but it also means one compile may run
hundreds of routing attempts.

The HC Valley Battery acceptance target currently tests 815 candidate
rectangles and selects a 41 x 17 routed bounding box. This is intentionally kept
small enough for CI while still exercising the same bottlenecks as a real
floorplanner.

Future parallel work should treat independent candidate rectangles and
multi-start placement attempts as coarse deterministic jobs before attempting
fine-grained parallel A*.

## Backend boundary

Alternative routers implement `RouterBackend`:

```python
class RouterBackend(Protocol):
    name: str

    def route(
        self,
        problem: RoutingProblem,
        options: ExecutionOptions,
    ) -> RoutingResult: ...
```

This keeps concurrency policy out of the compiler orchestration layer.

## Native-first direction

Python should remain the CLI, schema, pack-loading and reporting layer. The
router, future placement optimizer and any global solver hot loop should be
treated as native-core candidates. Rust is the preferred first target because
it gives predictable memory layout, safe parallelism and a clean path to Python
bindings later. C++ remains acceptable for third-party solver integration when
the dependency already exposes a stable C or C++ API.

AI-assisted maintenance changes the tradeoff: the project should prefer clear
high-performance data structures over intentionally slow beginner-friendly
code in hot paths. Public interfaces and tests must stay readable even if the
inner loops become lower-level.

The first native component is [`native/route_core`](../native/route_core), a
standalone Rust crate for deterministic single-net A*. It uses integer cell and
state ids, reusable workspace arrays and per-cell occupancy bitsets. It is not
yet wired into the Python `RouterBackend`; that binding is the next milestone.
The rationale is captured in [ADR 0001](adr/0001-native-routing-core.md).

## Parallel implementation rules

1. Keep deterministic single-job output as the reference.
2. Do not use Python threads for the pure-Python A* hot loop.
3. Give one scheduler ownership of the total CPU budget; avoid nested pools.
4. Prefer coarse process tasks or a native routing kernel that releases the
   GIL.
5. Route conflict-independent batches against an immutable occupancy snapshot.
6. Commit results in stable net-ID order and reroute conflicts in a later
   negotiated-congestion pass.
7. Compare one-job and multi-job outputs with semantic correctness tests.
8. Keep small projects serial when worker startup costs exceed expected work.

Independent whole-design processes already showed near-linear throughput on the
audit machine, so multi-start placement/routing is the safest first parallel
backend. Fine-grained parallel A* should come only after deterministic conflict
resolution exists.

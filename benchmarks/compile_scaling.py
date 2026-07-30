from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from time import perf_counter, process_time

from endfield_factory_compiler.compiler import compile_project
from endfield_factory_compiler.execution import ExecutionOptions
from endfield_factory_compiler.model import GridSpec, ProjectConstraints
from endfield_factory_compiler.pack import load_project, load_region_pack


ROOT = Path(__file__).resolve().parents[1]
DEMO_PROJECT = ROOT / "examples" / "control-core.json"


@dataclass
class BenchmarkRow:
    target_rate: int
    devices: int
    routes: int
    grid_cells: int
    wall_ms: float
    cpu_ms: float
    core_equivalents: float | None
    routing_ms: float
    expanded_states: int
    peak_frontier: int
    effective_jobs: int


def _rates(value: str) -> list[int]:
    try:
        rates = [int(item.strip()) for item in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "rates must be comma-separated integers"
        ) from exc
    if not rates or any(rate < 1 for rate in rates):
        raise argparse.ArgumentTypeError("rates must be positive")
    return rates


def run_benchmark(
    rates: list[int],
    repeats: int,
    jobs: int,
) -> list[BenchmarkRow]:
    base_project = load_project(DEMO_PROJECT)
    base_pack = load_region_pack(base_project.region_pack_path)
    rows: list[BenchmarkRow] = []

    for rate in rates:
        height = max(40, int(rate * 2.6) + 24)
        grid = GridSpec(
            width=96,
            height=height,
            max_power=1_000_000,
            obstacles=(),
        )
        pack = replace(base_pack, grid=grid)
        project = replace(
            base_project,
            targets={"control_core": float(rate)},
            constraints=ProjectConstraints(),
        )
        samples: list[tuple[float, float, object]] = []
        for _ in range(repeats):
            wall_start = perf_counter()
            cpu_start = process_time()
            result = compile_project(
                project,
                pack,
                options=ExecutionOptions(jobs=jobs),
            )
            wall = perf_counter() - wall_start
            cpu = process_time() - cpu_start
            samples.append((wall, cpu, result))

        middle = sorted(samples, key=lambda sample: sample[0])[len(samples) // 2]
        wall, cpu, result = middle
        rows.append(
            BenchmarkRow(
                target_rate=rate,
                devices=result.metrics.device_count,
                routes=result.metrics.route_count,
                grid_cells=grid.width * grid.height,
                wall_ms=wall * 1000,
                cpu_ms=cpu * 1000,
                # The Windows process CPU clock is too coarse for a trustworthy
                # ratio on very short runs.
                core_equivalents=cpu / wall if wall >= 0.05 else None,
                routing_ms=result.routing_stats.elapsed_seconds * 1000,
                expanded_states=result.routing_stats.expanded_states,
                peak_frontier=result.routing_stats.peak_frontier,
                effective_jobs=result.routing_stats.effective_jobs,
            )
        )
    return rows


def _print_table(rows: list[BenchmarkRow]) -> None:
    print(
        "rate devices routes grid_cells wall_ms cpu_ms cores "
        "routing_ms expanded peak_frontier jobs"
    )
    for row in rows:
        core_equivalents = (
            f"{row.core_equivalents:5.2f}"
            if row.core_equivalents is not None
            else "  n/a"
        )
        print(
            f"{row.target_rate:4} {row.devices:7} {row.routes:6} "
            f"{row.grid_cells:10} {row.wall_ms:7.2f} {row.cpu_ms:7.2f} "
            f"{core_equivalents} {row.routing_ms:10.2f} "
            f"{row.expanded_states:8} {row.peak_frontier:13} "
            f"{row.effective_jobs:4}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic compiler scaling benchmarks."
    )
    parser.add_argument(
        "--rates",
        type=_rates,
        default=_rates("8,32,64,128"),
        help="Comma-separated target rates (default: 8,32,64,128)",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=1,
        help="Runs per target rate; median wall time is reported",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Requested execution job budget",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
    )
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")

    rows = run_benchmark(args.rates, args.repeats, args.jobs)
    if args.format == "json":
        print(
            json.dumps(
                {
                    "logical_cpus": os.cpu_count(),
                    "rows": [asdict(row) for row in rows],
                },
                indent=2,
            )
        )
    else:
        _print_table(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

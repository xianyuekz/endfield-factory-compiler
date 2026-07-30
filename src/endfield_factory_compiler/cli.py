from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .compiler import compile_project
from .execution import (
    ExecutionOptions,
    PERFORMANCE_PROFILES,
    resolve_performance_profile,
)
from .floorplan import FloorplanSearchError
from .model import FloorplanSearchOptions
from .pack import load_project, load_region_pack
from .placement import PlacementError
from .render import render_svg
from .report import render_markdown
from .synthesis import synthesize


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="efc",
        description=(
            "Offline factory synthesis, placement, routing and DRC prototype."
        ),
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    compile_command = commands.add_parser(
        "compile", help="Compile a factory project"
    )
    compile_command.add_argument("project", type=Path)
    compile_command.add_argument(
        "--out",
        type=Path,
        default=Path("build"),
        help="Output directory (default: build)",
    )
    compile_command.add_argument(
        "--profile",
        choices=sorted(PERFORMANCE_PROFILES),
        default="balanced",
        help=(
            "Resource profile for low-end or quality-oriented runs "
            "(default: balanced)"
        ),
    )
    compile_command.add_argument(
        "--jobs",
        type=int,
        default=None,
        help=(
            "Requested router job budget; the current reference backend "
            "reports a serial fallback when greater than 1"
        ),
    )
    compile_command.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Deterministic backend seed (default: 0)",
    )
    compile_command.add_argument(
        "--time-limit",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Soft routing time limit in seconds",
    )
    compile_command.add_argument(
        "--min-area",
        action="store_true",
        help=(
            "Search for the smallest feasible routed bounding box using the "
            "current compact floorplanning strategy"
        ),
    )
    compile_command.add_argument(
        "--floorplan-max-candidates",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Maximum candidate rectangles tested by --min-area "
            "(default comes from --profile)"
        ),
    )

    validate_command = commands.add_parser(
        "validate-pack", help="Validate a region pack"
    )
    validate_command.add_argument("pack", type=Path)

    validate_project_command = commands.add_parser(
        "validate-project",
        help="Validate a project and its logical production graph",
    )
    validate_project_command.add_argument("project", type=Path)
    return parser


def _compile(
    project_path: Path,
    output: Path,
    *,
    profile: str,
    jobs: int | None,
    seed: int,
    time_limit: float | None,
    min_area: bool,
    floorplan_max_candidates: int | None,
) -> int:
    project = load_project(project_path)
    pack = load_region_pack(project.region_pack_path)
    selected_profile = resolve_performance_profile(profile)
    selected_jobs = jobs if jobs is not None else 1
    options = ExecutionOptions(
        profile=profile,
        jobs=selected_jobs,
        seed=seed,
        time_limit_seconds=time_limit,
    )
    floorplan = FloorplanSearchOptions(
        enabled=min_area,
        max_candidates=(
            floorplan_max_candidates
            if floorplan_max_candidates is not None
            else selected_profile.floorplan_max_candidates
        ),
    )
    result = compile_project(project, pack, options=options, floorplan=floorplan)

    output.mkdir(parents=True, exist_ok=True)
    plan_path = output / "plan.json"
    svg_path = output / "layout.svg"
    report_path = output / "report.md"
    plan_path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    svg_path.write_text(
        render_svg(
            project,
            pack,
            result.synthesis,
            result.layout,
            result.metrics,
            result.diagnostics,
        ),
        encoding="utf-8",
        newline="\n",
    )
    report_path.write_text(
        render_markdown(result),
        encoding="utf-8",
        newline="\n",
    )

    errors = sum(item.severity == "error" for item in result.diagnostics)
    warnings = sum(item.severity == "warning" for item in result.diagnostics)
    print(f"Compiled {project.name!r}")
    print(f"  Profile: {options.profile}")
    print(
        f"  {len(result.layout.devices)} devices, "
        f"{len(result.layout.routes)} routes, "
        f"{result.metrics.route_tiles} route tiles"
    )
    print(
        f"  {result.synthesis.total_power:.1f} power, "
        f"{result.metrics.area_utilization_percent:.1f}% area, "
        f"{result.metrics.bounding_box_width}x"
        f"{result.metrics.bounding_box_height} bounding box"
    )
    if result.floorplan_search is not None:
        search = result.floorplan_search
        print(
            f"  Floorplan: {search.selected_width}x{search.selected_height} "
            f"({search.selected_area} tiles), "
            f"{search.candidates_tested} candidate(s), "
            f"lower bound {search.lower_bound_area}"
        )
    print(
        f"  Router: {result.routing_stats.backend_name}, "
        f"{result.routing_stats.effective_jobs}/"
        f"{result.routing_stats.requested_jobs} jobs, "
        f"{result.routing_stats.expanded_states} expanded states, "
        f"{result.routing_stats.elapsed_seconds * 1000:.2f} ms"
    )
    print(f"  DRC: {errors} error(s), {warnings} warning(s)")
    print(f"  Plan: {plan_path}")
    print(f"  SVG:  {svg_path}")
    print(f"  Report: {report_path}")
    return 1 if result.has_errors else 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "compile":
            return _compile(
                args.project,
                args.out,
                profile=args.profile,
                jobs=args.jobs,
                seed=args.seed,
                time_limit=args.time_limit,
                min_area=args.min_area,
                floorplan_max_candidates=args.floorplan_max_candidates,
            )
        if args.command == "validate-pack":
            pack = load_region_pack(args.pack)
            print(
                f"Valid region pack {pack.id!r} version {pack.version}: "
                f"{len(pack.devices)} devices, {len(pack.recipes)} recipes"
            )
            return 0
        if args.command == "validate-project":
            project = load_project(args.project)
            pack = load_region_pack(project.region_pack_path)
            synthesis = synthesize(pack, project.targets)
            print(
                f"Valid project {project.name!r}: "
                f"{len(synthesis.nodes)} production stages, "
                f"{sum(node.machine_count for node in synthesis.nodes)} devices"
            )
            return 0
    except (FloorplanSearchError, PlacementError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

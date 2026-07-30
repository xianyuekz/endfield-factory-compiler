from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .compiler import compile_project
from .pack import PackError, load_project, load_region_pack
from .placement import PlacementError
from .render import render_svg
from .synthesis import SynthesisError


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

    validate_command = commands.add_parser(
        "validate-pack", help="Validate a region pack"
    )
    validate_command.add_argument("pack", type=Path)
    return parser


def _compile(project_path: Path, output: Path) -> int:
    project = load_project(project_path)
    pack = load_region_pack(project.region_pack_path)
    result = compile_project(project, pack)

    output.mkdir(parents=True, exist_ok=True)
    plan_path = output / "plan.json"
    svg_path = output / "layout.svg"
    plan_path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    svg_path.write_text(
        render_svg(
            project,
            pack,
            result.synthesis,
            result.layout,
            result.diagnostics,
        ),
        encoding="utf-8",
    )

    errors = sum(item.severity == "error" for item in result.diagnostics)
    print(f"Compiled {project.name!r}")
    print(
        f"  {len(result.layout.devices)} devices, "
        f"{len(result.layout.routes)} routes, "
        f"{result.synthesis.total_power:.1f} power"
    )
    print(f"  DRC: {errors} error(s)")
    print(f"  Plan: {plan_path}")
    print(f"  SVG:  {svg_path}")
    return 1 if result.has_errors else 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "compile":
            return _compile(args.project, args.out)
        if args.command == "validate-pack":
            pack = load_region_pack(args.pack)
            print(
                f"Valid region pack {pack.id!r} version {pack.version}: "
                f"{len(pack.devices)} devices, {len(pack.recipes)} recipes"
            )
            return 0
    except (PackError, PlacementError, SynthesisError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


from __future__ import annotations

import hashlib
import html

from .model import (
    Diagnostic,
    LayoutResult,
    Project,
    RegionPack,
    SynthesisResult,
)


def _color(item: str) -> str:
    digest = hashlib.sha256(item.encode("utf-8")).digest()
    hue = int.from_bytes(digest[:2], "big") % 360
    return f"hsl({hue} 72% 58%)"


def _label(value: str) -> str:
    return html.escape(value.replace("_", " ").title())


def render_svg(
    project: Project,
    pack: RegionPack,
    synthesis: SynthesisResult,
    layout: LayoutResult,
    diagnostics: list[Diagnostic],
) -> str:
    cell = 18
    top = 74
    left = 28
    panel = 300
    grid_width = pack.grid.width * cell
    grid_height = pack.grid.height * cell
    width = left + grid_width + panel + 32
    height = top + grid_height + 36
    error_count = sum(item.severity == "error" for item in diagnostics)

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}">'
        ),
        "<defs>",
        (
            '<pattern id="grid" width="18" height="18" '
            'patternUnits="userSpaceOnUse">'
            '<path d="M 18 0 L 0 0 0 18" fill="none" '
            'stroke="#263244" stroke-width="0.6"/>'
            "</pattern>"
        ),
        (
            '<pattern id="obstacle" width="8" height="8" '
            'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            '<rect width="4" height="8" fill="#475569"/>'
            "</pattern>"
        ),
        (
            '<filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">'
            '<feDropShadow dx="0" dy="2" stdDeviation="2" '
            'flood-color="#000" flood-opacity=".35"/>'
            "</filter>"
        ),
        "</defs>",
        '<rect width="100%" height="100%" fill="#0b1120"/>',
        (
            f'<text x="{left}" y="32" fill="#f8fafc" font-size="22" '
            f'font-family="Inter,Segoe UI,sans-serif" font-weight="700">'
            f"{html.escape(project.name)}</text>"
        ),
        (
            f'<text x="{left}" y="54" fill="#94a3b8" font-size="12" '
            f'font-family="Inter,Segoe UI,sans-serif">'
            f"{html.escape(pack.name)} · {len(layout.devices)} devices · "
            f"{len(layout.routes)} routes · {error_count} DRC errors</text>"
        ),
        (
            f'<rect x="{left}" y="{top}" width="{grid_width}" '
            f'height="{grid_height}" rx="4" fill="#111827"/>'
        ),
        (
            f'<rect x="{left}" y="{top}" width="{grid_width}" '
            f'height="{grid_height}" rx="4" fill="url(#grid)"/>'
        ),
    ]

    for obstacle in pack.grid.obstacles:
        parts.append(
            f'<rect x="{left + obstacle.x * cell}" '
            f'y="{top + obstacle.y * cell}" '
            f'width="{obstacle.width * cell}" '
            f'height="{obstacle.height * cell}" fill="url(#obstacle)" '
            'stroke="#64748b" stroke-width="1"/>'
        )

    for route in layout.routes:
        if not route.points:
            continue
        points = " ".join(
            f"{left + x * cell + cell / 2:.1f},{top + y * cell + cell / 2:.1f}"
            for x, y in route.points
        )
        color = _color(route.item)
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="#020617" '
            'stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>'
        )
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" '
            'stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
        )

    for device in layout.devices:
        recipe = pack.recipes[device.recipe_id]
        x = left + device.rect.x * cell
        y = top + device.rect.y * cell
        device_width = device.rect.width * cell
        device_height = device.rect.height * cell
        parts.extend(
            [
                (
                    f'<rect x="{x}" y="{y}" width="{device_width}" '
                    f'height="{device_height}" rx="5" fill="#1e293b" '
                    'stroke="#7dd3fc" stroke-width="1.5" filter="url(#shadow)"/>'
                ),
                (
                    f'<text x="{x + device_width / 2:.1f}" '
                    f'y="{y + device_height / 2 - 3:.1f}" fill="#f8fafc" '
                    'font-size="10" text-anchor="middle" '
                    f'font-family="Inter,Segoe UI,sans-serif">{_label(recipe.name)}</text>'
                ),
                (
                    f'<text x="{x + device_width / 2:.1f}" '
                    f'y="{y + device_height / 2 + 11:.1f}" fill="#94a3b8" '
                    'font-size="8" text-anchor="middle" '
                    f'font-family="Inter,Segoe UI,sans-serif">{html.escape(device.id)}</text>'
                ),
            ]
        )

    panel_x = left + grid_width + 24
    parts.extend(
        [
            (
                f'<text x="{panel_x}" y="{top + 18}" fill="#f8fafc" '
                'font-size="15" font-weight="700" '
                'font-family="Inter,Segoe UI,sans-serif">Synthesis report</text>'
            ),
            (
                f'<text x="{panel_x}" y="{top + 45}" fill="#94a3b8" '
                'font-size="11" font-family="Inter,Segoe UI,sans-serif">'
                f"Power: {synthesis.total_power:.1f} / {pack.grid.max_power:.1f}</text>"
            ),
        ]
    )
    panel_y = top + 70
    for node in synthesis.nodes:
        parts.extend(
            [
                (
                    f'<circle cx="{panel_x + 5}" cy="{panel_y - 4}" r="4" '
                    f'fill="{_color(node.item)}"/>'
                ),
                (
                    f'<text x="{panel_x + 16}" y="{panel_y}" fill="#e2e8f0" '
                    'font-size="10" font-family="Inter,Segoe UI,sans-serif">'
                    f"{_label(node.item)} × {node.machine_count}</text>"
                ),
                (
                    f'<text x="{panel_x + 16}" y="{panel_y + 14}" fill="#64748b" '
                    'font-size="9" font-family="Inter,Segoe UI,sans-serif">'
                    f"{node.required_rate:.1f}/min required · "
                    f"{node.capacity_rate:.1f}/min available</text>"
                ),
            ]
        )
        panel_y += 40

    panel_y += 10
    parts.append(
        f'<text x="{panel_x}" y="{panel_y}" fill="#f8fafc" font-size="13" '
        'font-weight="700" font-family="Inter,Segoe UI,sans-serif">Raw inputs</text>'
    )
    panel_y += 23
    for item, rate in synthesis.source_rates.items():
        parts.append(
            f'<text x="{panel_x}" y="{panel_y}" fill="#cbd5e1" font-size="10" '
            f'font-family="Inter,Segoe UI,sans-serif">{_label(item)} · '
            f"{rate:.1f}/min</text>"
        )
        panel_y += 17

    status_color = "#34d399" if error_count == 0 else "#fb7185"
    status_text = "DRC CLEAN" if error_count == 0 else f"DRC: {error_count} ERROR(S)"
    parts.append(
        f'<rect x="{panel_x}" y="{top + grid_height - 42}" width="246" '
        f'height="30" rx="6" fill="{status_color}" opacity=".16"/>'
    )
    parts.append(
        f'<text x="{panel_x + 12}" y="{top + grid_height - 22}" '
        f'fill="{status_color}" font-size="11" font-weight="700" '
        f'font-family="Inter,Segoe UI,sans-serif">{status_text}</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


from __future__ import annotations

from collections import defaultdict

from .model import PlacedDevice, Rect, RegionPack, SynthesisResult


class PlacementError(RuntimeError):
    """Raised when devices do not fit inside the selected region."""


def _rect_with_halo(rect: Rect, grid_width: int, grid_height: int) -> set[tuple[int, int]]:
    return {
        (x, y)
        for x in range(max(0, rect.x - 1), min(grid_width, rect.x + rect.width + 1))
        for y in range(max(0, rect.y - 1), min(grid_height, rect.y + rect.height + 1))
    }


def place_devices(
    pack: RegionPack, synthesis: SynthesisResult
) -> list[PlacedDevice]:
    occupied = set().union(*(obstacle.cells() for obstacle in pack.grid.obstacles))
    devices: list[PlacedDevice] = []
    nodes_by_depth: dict[int, list] = defaultdict(list)
    for node in synthesis.nodes:
        nodes_by_depth[node.depth].append(node)

    x_cursor = 3
    for depth in sorted(nodes_by_depth):
        depth_nodes = nodes_by_depth[depth]
        max_width = max(
            pack.devices[pack.recipes[node.recipe_id].device].width
            for node in depth_nodes
        )
        y_cursor = 2
        depth_right = x_cursor

        for node in depth_nodes:
            recipe = pack.recipes[node.recipe_id]
            device_spec = pack.devices[recipe.device]
            for instance in range(1, node.machine_count + 1):
                placed_rect: Rect | None = None
                candidate_x = x_cursor
                candidate_y = y_cursor

                while candidate_x + device_spec.width + 1 < pack.grid.width:
                    while candidate_y + device_spec.height + 1 < pack.grid.height:
                        candidate = Rect(
                            candidate_x,
                            candidate_y,
                            device_spec.width,
                            device_spec.height,
                        )
                        if not (_rect_with_halo(
                            candidate, pack.grid.width, pack.grid.height
                        ) & occupied):
                            placed_rect = candidate
                            break
                        candidate_y += 1
                    if placed_rect is not None:
                        break
                    candidate_x += max_width + 3
                    candidate_y = 2

                if placed_rect is None:
                    raise PlacementError(
                        f"Cannot place {node.recipe_id} instance {instance}; "
                        f"region {pack.id!r} is full"
                    )

                placed = PlacedDevice(
                    id=f"{node.recipe_id}-{instance}",
                    recipe_id=node.recipe_id,
                    device_id=recipe.device,
                    output_item=recipe.output_item,
                    depth=depth,
                    rect=placed_rect,
                    input_items=tuple(recipe.inputs),
                )
                devices.append(placed)
                occupied.update(placed_rect.cells())
                y_cursor = placed_rect.y + placed_rect.height + 2
                depth_right = max(depth_right, placed_rect.x + placed_rect.width)

        x_cursor = depth_right + 5

    return devices


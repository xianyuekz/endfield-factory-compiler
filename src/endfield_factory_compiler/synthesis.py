from __future__ import annotations

import math
from collections import defaultdict

from .model import RegionPack, SynthesisNode, SynthesisResult


class SynthesisError(ValueError):
    """Raised when a production graph cannot be synthesized."""


def synthesize(pack: RegionPack, targets: dict[str, float]) -> SynthesisResult:
    recipe_by_output = pack.recipe_by_output()
    node_rates: dict[str, float] = defaultdict(float)
    source_rates: dict[str, float] = defaultdict(float)

    def expand(item: str, rate: float, stack: tuple[str, ...]) -> None:
        if item not in pack.items:
            raise SynthesisError(f"Unknown target or ingredient: {item!r}")
        recipe = recipe_by_output.get(item)
        if recipe is None:
            source_rates[item] += rate
            return
        if item in stack:
            cycle = " -> ".join((*stack, item))
            raise SynthesisError(
                f"Recipe cycle detected ({cycle}); schema v1 supports DAGs only"
            )
        node_rates[recipe.id] += rate
        next_stack = (*stack, item)
        for input_item, input_amount in recipe.inputs.items():
            input_rate = rate * input_amount / recipe.output_amount
            expand(input_item, input_rate, next_stack)

    for item, rate in targets.items():
        expand(item, rate, ())

    depth_cache: dict[str, int] = {}

    def item_depth(item: str, stack: tuple[str, ...] = ()) -> int:
        if item in depth_cache:
            return depth_cache[item]
        recipe = recipe_by_output.get(item)
        if recipe is None:
            depth_cache[item] = 0
            return 0
        if item in stack:
            raise SynthesisError(f"Recipe cycle detected while ordering {item!r}")
        depth = 1 + max(
            (item_depth(input_item, (*stack, item)) for input_item in recipe.inputs),
            default=0,
        )
        depth_cache[item] = depth
        return depth

    nodes: list[SynthesisNode] = []
    total_power = 0.0
    for recipe_id, required_rate in node_rates.items():
        recipe = pack.recipes[recipe_id]
        device = pack.devices[recipe.device]
        capacity_per_machine = recipe.output_rate_per_minute
        machine_count = math.ceil(required_rate / capacity_per_machine - 1e-12)
        capacity_rate = machine_count * capacity_per_machine
        power = machine_count * device.power
        input_rates = {
            item: required_rate * amount / recipe.output_amount
            for item, amount in recipe.inputs.items()
        }
        nodes.append(
            SynthesisNode(
                recipe_id=recipe_id,
                item=recipe.output_item,
                required_rate=required_rate,
                machine_count=machine_count,
                capacity_rate=capacity_rate,
                depth=item_depth(recipe.output_item),
                input_rates=input_rates,
                power=power,
            )
        )
        total_power += power

    nodes.sort(key=lambda node: (node.depth, node.recipe_id))
    return SynthesisResult(
        targets=dict(targets),
        nodes=nodes,
        source_rates=dict(sorted(source_rates.items())),
        total_power=total_power,
    )


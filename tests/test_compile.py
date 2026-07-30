from collections import defaultdict
import unittest
from dataclasses import replace
from pathlib import Path

from endfield_factory_compiler.compiler import compile_project
from endfield_factory_compiler.drc import run_drc
from endfield_factory_compiler.metrics import calculate_metrics
from endfield_factory_compiler.model import ProjectConstraints
from endfield_factory_compiler.pack import load_project, load_region_pack
from endfield_factory_compiler.render import render_svg
from endfield_factory_compiler.report import render_markdown


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "examples" / "control-core.json"
HC_VALLEY_BATTERY_PROJECT = ROOT / "examples" / "hc-valley-battery.json"


class CompilationTests(unittest.TestCase):
    def test_demo_compiles_cleanly(self):
        project = load_project(PROJECT)
        pack = load_region_pack(project.region_pack_path)
        result = compile_project(project, pack)
        errors = [
            diagnostic
            for diagnostic in result.diagnostics
            if diagnostic.severity == "error"
        ]
        self.assertEqual(errors, [])
        self.assertEqual(len(result.layout.devices), 13)
        self.assertTrue(result.layout.routes)
        self.assertTrue(all(route.routed for route in result.layout.routes))

        plan = result.to_dict()
        self.assertEqual(plan["format_version"], 1)
        self.assertEqual(plan["region"]["id"], "demo-valley")
        self.assertEqual(plan["project"]["constraints"]["max_devices"], 16)
        self.assertEqual(plan["metrics"]["device_count"], 13)
        self.assertGreater(plan["metrics"]["route_tiles"], 0)
        self.assertLess(plan["metrics"]["area_utilization_percent"], 100)

        svg = render_svg(
            project,
            pack,
            result.synthesis,
            result.layout,
            result.metrics,
            result.diagnostics,
        )
        self.assertIn("<svg", svg)
        self.assertIn("DRC CLEAN", svg)
        self.assertIn("Area:", svg)

        report = render_markdown(result)
        self.assertIn("**PASS**", report)
        self.assertIn("## Production", report)
        self.assertIn("Control Core", report)

    def test_hc_valley_battery_compiles_cleanly(self):
        project = load_project(HC_VALLEY_BATTERY_PROJECT)
        pack = load_region_pack(project.region_pack_path)
        result = compile_project(project, pack)

        errors = [
            diagnostic
            for diagnostic in result.diagnostics
            if diagnostic.severity == "error"
        ]
        self.assertEqual(errors, [])
        self.assertEqual(result.synthesis.targets, {"hc_valley_battery": 6.0})
        self.assertEqual(sum(node.machine_count for node in result.synthesis.nodes), 28)
        self.assertTrue(all(route.routed for route in result.layout.routes))
        self.assertLessEqual(
            result.synthesis.total_power,
            project.constraints.max_power,
        )
        self.assertLessEqual(
            result.metrics.device_count,
            project.constraints.max_devices,
        )
        self.assertLessEqual(
            result.metrics.route_tiles,
            project.constraints.max_route_tiles,
        )

        machines_by_recipe = {
            node.recipe_id: node.machine_count for node in result.synthesis.nodes
        }
        self.assertEqual(machines_by_recipe["package_hc_valley_battery"], 1)
        self.assertEqual(machines_by_recipe["fit_steel_part"], 2)
        self.assertEqual(machines_by_recipe["grind_dense_originium_powder"], 3)

        plan = result.to_dict()
        self.assertEqual(plan["region"]["id"], "valley-iv-research")
        self.assertEqual(plan["metrics"]["device_count"], 28)
        self.assertGreater(plan["metrics"]["route_tiles"], 0)

        svg = render_svg(
            project,
            pack,
            result.synthesis,
            result.layout,
            result.metrics,
            result.diagnostics,
        )
        self.assertIn("6 HC Valley Batteries per Minute", svg)
        self.assertIn("DRC CLEAN", svg)

        report = render_markdown(result)
        self.assertIn("**PASS**", report)
        self.assertIn("HC Valley Battery", report)

    def test_project_constraints_are_checked(self):
        project = load_project(PROJECT)
        project = replace(
            project,
            constraints=ProjectConstraints(
                max_power=100,
                max_devices=2,
                max_route_tiles=10,
            ),
        )
        pack = load_region_pack(project.region_pack_path)
        result = compile_project(project, pack)
        codes = {
            diagnostic.code
            for diagnostic in result.diagnostics
            if diagnostic.severity == "error"
        }
        self.assertEqual(
            codes,
            {
                "PROJECT_POWER_CONSTRAINT_EXCEEDED",
                "PROJECT_DEVICE_CONSTRAINT_EXCEEDED",
                "PROJECT_ROUTE_CONSTRAINT_EXCEEDED",
            },
        )

    def test_physical_flow_respects_each_machine_capacity(self):
        project = load_project(PROJECT)
        pack = load_region_pack(project.region_pack_path)
        result = compile_project(project, pack)
        devices = {device.id: device for device in result.layout.devices}

        outgoing_rates = defaultdict(float)
        for route in result.layout.routes:
            if route.source in devices:
                outgoing_rates[route.source] += route.required_rate

        for device_id, assigned_rate in outgoing_rates.items():
            device = devices[device_id]
            capacity = pack.recipes[
                device.recipe_id
            ].output_rate_per_minute
            self.assertLessEqual(
                assigned_rate,
                capacity + 1e-9,
                f"{device_id} is assigned more output than it can produce",
            )

        incoming_rates = defaultdict(float)
        for route in result.layout.routes:
            incoming_rates[(route.sink, route.item)] += route.required_rate
        consumers_by_recipe = defaultdict(list)
        for device in result.layout.devices:
            consumers_by_recipe[device.recipe_id].append(device)
        for node in result.synthesis.nodes:
            consumers = consumers_by_recipe[node.recipe_id]
            for consumer in consumers:
                for item, total_rate in node.input_rates.items():
                    expected = total_rate / len(consumers)
                    self.assertAlmostEqual(
                        incoming_rates[(consumer.id, item)],
                        expected,
                        msg=f"{consumer.id} does not receive enough {item}",
                    )

    def test_drc_rejects_an_overloaded_producer(self):
        project = load_project(PROJECT)
        pack = load_region_pack(project.region_pack_path)
        result = compile_project(project, pack)
        internal_route = next(
            route
            for route in result.layout.routes
            if not route.source.startswith(("external:", "unallocated:"))
        )
        internal_route.required_rate += 100
        metrics = calculate_metrics(pack, result.synthesis, result.layout)
        diagnostics = run_drc(
            project,
            pack,
            result.synthesis,
            result.layout,
            metrics,
        )
        self.assertIn(
            "PRODUCER_CAPACITY_EXCEEDED",
            {diagnostic.code for diagnostic in diagnostics},
        )


if __name__ == "__main__":
    unittest.main()

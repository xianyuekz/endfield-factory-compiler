import unittest
from dataclasses import replace
from pathlib import Path

from endfield_factory_compiler.compiler import compile_project
from endfield_factory_compiler.model import ProjectConstraints
from endfield_factory_compiler.pack import load_project, load_region_pack
from endfield_factory_compiler.render import render_svg
from endfield_factory_compiler.report import render_markdown


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "examples" / "control-core.json"


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


if __name__ == "__main__":
    unittest.main()

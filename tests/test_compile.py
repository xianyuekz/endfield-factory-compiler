import unittest
from pathlib import Path

from endfield_factory_compiler.compiler import compile_project
from endfield_factory_compiler.pack import load_project, load_region_pack
from endfield_factory_compiler.render import render_svg


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

        svg = render_svg(
            project,
            pack,
            result.synthesis,
            result.layout,
            result.diagnostics,
        )
        self.assertIn("<svg", svg)
        self.assertIn("DRC CLEAN", svg)


if __name__ == "__main__":
    unittest.main()


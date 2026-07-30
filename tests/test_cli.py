import tempfile
import unittest
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from endfield_factory_compiler.cli import main


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "examples" / "control-core.json"
PACK = ROOT / "region-packs" / "demo-valley" / "region.json"


class CliTests(unittest.TestCase):
    def test_validate_commands(self):
        output = StringIO()
        with redirect_stdout(output):
            pack_status = main(["validate-pack", str(PACK)])
            project_status = main(["validate-project", str(PROJECT)])
        self.assertEqual(pack_status, 0)
        self.assertEqual(project_status, 0)
        self.assertIn("Valid region pack", output.getvalue())
        self.assertIn("Valid project", output.getvalue())

    def test_compile_writes_all_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with redirect_stdout(StringIO()):
                status = main(["compile", str(PROJECT), "--out", str(output)])
            self.assertEqual(status, 0)
            self.assertTrue((output / "plan.json").is_file())
            self.assertTrue((output / "layout.svg").is_file())
            self.assertTrue((output / "report.md").is_file())
            self.assertIn(
                "**PASS**",
                (output / "report.md").read_text(encoding="utf-8"),
            )

    def test_compile_reports_serial_job_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            output = StringIO()
            with redirect_stdout(output):
                status = main(
                    [
                        "compile",
                        str(PROJECT),
                        "--out",
                        directory,
                        "--jobs",
                        "4",
                    ]
                )
            self.assertEqual(status, 0)
            self.assertIn("1/4 jobs", output.getvalue())
            self.assertIn("0 error(s), 1 warning(s)", output.getvalue())

    def test_compile_can_search_min_area_floorplan(self):
        with tempfile.TemporaryDirectory() as directory:
            output = StringIO()
            with redirect_stdout(output):
                status = main(
                    [
                        "compile",
                        str(PROJECT),
                        "--out",
                        directory,
                        "--min-area",
                        "--floorplan-max-candidates",
                        "200",
                    ]
                )
            self.assertEqual(status, 0)
            self.assertIn("Floorplan:", output.getvalue())
            plan = json.loads(
                (Path(directory) / "plan.json").read_text(encoding="utf-8")
            )
            self.assertTrue(plan["floorplan_search"]["enabled"])
            self.assertLessEqual(
                plan["floorplan_search"]["selected_area"],
                plan["floorplan_search"]["baseline_area"],
            )


if __name__ == "__main__":
    unittest.main()

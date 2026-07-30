import json
import tempfile
import unittest
from pathlib import Path

from endfield_factory_compiler.pack import PackError, load_region_pack


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "region-packs" / "demo-valley" / "region.json"
VALLEY_RESEARCH_PACK = ROOT / "region-packs" / "valley-iv-research" / "region.json"


class RegionPackTests(unittest.TestCase):
    def test_demo_pack_loads(self):
        pack = load_region_pack(PACK)
        self.assertEqual(pack.id, "demo-valley")
        self.assertEqual(len(pack.devices), 4)
        self.assertEqual(len(pack.recipes), 5)
        self.assertEqual(pack.recipe_by_output()["control_core"].device, "constructor")
        self.assertTrue(pack.logistics.allow_crossings)
        self.assertEqual(pack.logistics.crossing_penalty, 8)
        self.assertEqual(pack.logistics.bend_penalty, 0.4)

    def test_valley_research_pack_loads(self):
        pack = load_region_pack(VALLEY_RESEARCH_PACK)
        self.assertEqual(pack.id, "valley-iv-research")
        self.assertIn("hc_valley_battery", pack.items)
        self.assertEqual(len(pack.devices), 6)
        self.assertEqual(len(pack.recipes), 10)
        self.assertEqual(pack.logistics.tile_capacity_per_minute, 120)

        battery_recipe = pack.recipe_by_output()["hc_valley_battery"]
        self.assertEqual(battery_recipe.cycle_seconds, 10)
        self.assertEqual(
            battery_recipe.inputs,
            {
                "steel_part": 10.0,
                "dense_originium_powder": 15.0,
            },
        )

    def test_missing_pack_is_reported(self):
        with self.assertRaises(PackError):
            load_region_pack(ROOT / "does-not-exist.json")

    def test_boolean_fields_do_not_accept_strings(self):
        data = json.loads(PACK.read_text(encoding="utf-8"))
        data["logistics"]["allow_crossings"] = "false"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "region.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(PackError, "must be true or false"):
                load_region_pack(path)

    def test_grid_dimensions_must_be_whole_numbers(self):
        data = json.loads(PACK.read_text(encoding="utf-8"))
        data["grid"]["width"] = 63.5
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "region.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(PackError, "whole number"):
                load_region_pack(path)


if __name__ == "__main__":
    unittest.main()

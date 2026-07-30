import unittest
from pathlib import Path

from endfield_factory_compiler.pack import PackError, load_region_pack


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "region-packs" / "demo-valley" / "region.json"


class RegionPackTests(unittest.TestCase):
    def test_demo_pack_loads(self):
        pack = load_region_pack(PACK)
        self.assertEqual(pack.id, "demo-valley")
        self.assertEqual(len(pack.devices), 4)
        self.assertEqual(len(pack.recipes), 5)
        self.assertEqual(pack.recipe_by_output()["control_core"].device, "constructor")

    def test_missing_pack_is_reported(self):
        with self.assertRaises(PackError):
            load_region_pack(ROOT / "does-not-exist.json")


if __name__ == "__main__":
    unittest.main()


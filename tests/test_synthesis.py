import unittest
from pathlib import Path

from endfield_factory_compiler.pack import load_region_pack
from endfield_factory_compiler.synthesis import synthesize


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "region-packs" / "demo-valley" / "region.json"


class SynthesisTests(unittest.TestCase):
    def setUp(self):
        self.pack = load_region_pack(PACK)

    def test_control_core_machine_counts(self):
        result = synthesize(self.pack, {"control_core": 8})
        counts = {node.recipe_id: node.machine_count for node in result.nodes}
        self.assertEqual(
            counts,
            {
                "make_iron_powder": 2,
                "make_copper_wire": 2,
                "make_frame": 4,
                "make_circuit": 3,
                "make_control_core": 2,
            },
        )
        self.assertEqual(result.source_rates["iron_ore"], 48)
        self.assertEqual(result.source_rates["copper_ore"], 16)
        self.assertEqual(result.source_rates["quartz"], 16)
        self.assertEqual(result.total_power, 304)

    def test_unknown_target_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown target"):
            synthesize(self.pack, {"missing_item": 1})


if __name__ == "__main__":
    unittest.main()


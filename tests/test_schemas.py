import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SchemaTests(unittest.TestCase):
    def test_json_schemas_and_examples_are_valid_json(self):
        paths = [
            ROOT / "schemas" / "project.schema.json",
            ROOT / "schemas" / "region-pack.schema.json",
            ROOT / "examples" / "control-core.json",
            ROOT / "examples" / "hc-valley-battery.json",
            ROOT / "region-packs" / "demo-valley" / "region.json",
            ROOT / "region-packs" / "valley-iv-research" / "region.json",
        ]
        documents = [
            json.loads(path.read_text(encoding="utf-8")) for path in paths
        ]
        self.assertEqual(
            documents[0]["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )
        self.assertEqual(documents[1]["properties"]["schema_version"]["const"], 1)
        self.assertEqual(documents[2]["schema_version"], 1)
        self.assertEqual(documents[3]["schema_version"], 1)
        self.assertEqual(documents[4]["schema_version"], 1)
        self.assertEqual(documents[5]["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()

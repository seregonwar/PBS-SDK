import copy
import json
from pathlib import Path
import unittest

from pbs_sdk import Plugin, Metric
from scripts.validate import validate_manifest_document


class ToolPanels(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((Path(__file__).resolve().parents[1] /
            "examples/stream-inspector/plugin.json").read_text(encoding="utf-8"))

    def check_manifest(self, valid):
        errors = validate_manifest_document(json.dumps(self.manifest))
        self.assertEqual(not errors, valid, errors)

    def test_example_and_compatibility(self):
        self.check_manifest(True)
        self.manifest["schema"] = 3
        self.check_manifest(False)

    def test_permission_unknown_and_duplicate_metrics(self):
        original = copy.deepcopy(self.manifest)
        for metrics in (["account.token"], ["stream.frames", "stream.frames"], []):
            self.manifest = copy.deepcopy(original)
            self.manifest["panels"][0]["metrics"] = metrics
            self.check_manifest(False)
        self.manifest = original
        self.manifest["permissions"] = []
        self.check_manifest(False)

    def test_limits_ids_and_text(self):
        original = copy.deepcopy(self.manifest)
        for field, value in (("id", "Bad ID"), ("title", "x\x00"),
                             ("title", "é" * 60)):
            self.manifest = copy.deepcopy(original)
            self.manifest["panels"][0][field] = value
            self.check_manifest(False)
        self.manifest = original
        self.manifest["panels"].append(copy.deepcopy(original["panels"][0]))
        self.check_manifest(False)

    def test_builder_isolation(self):
        plugin = Plugin("dev.test.tools", "Tools", "1.0.0", "", "Test")
        plugin.panel("stream", title="Stream", description="",
                     metrics=[Metric.STREAM_DECODER])
        result = plugin.manifest()
        self.assertEqual(result["schema"], 4)
        result["panels"][0]["metrics"].clear()
        self.assertTrue(plugin.manifest()["panels"][0]["metrics"])
        self.assertFalse(validate_manifest_document(plugin.render()))


if __name__ == "__main__":
    unittest.main()

import copy
import json
from pathlib import Path
import unittest

from scripts.validate import validate_manifest_document


class ScriptRuntime(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(
            (Path(__file__).resolve().parents[1] /
             "examples/script-panel/plugin.json").read_text(encoding="utf-8")
        )

    def check_manifest(self, valid):
        errors = validate_manifest_document(json.dumps(self.manifest))
        self.assertEqual(not errors, valid, errors)

    def test_example_and_api_major(self):
        self.check_manifest(True)
        original = copy.deepcopy(self.manifest)
        for api in (1, 3, "2"):
            self.manifest = copy.deepcopy(original)
            self.manifest["api_version"] = api
            self.check_manifest(False)

    def test_runtime_is_required_and_validated(self):
        original = copy.deepcopy(self.manifest)
        self.manifest = copy.deepcopy(original)
        del self.manifest["runtime"]
        self.check_manifest(False)

        for language in ("js", "python", "Lua", ""):
            self.manifest = copy.deepcopy(original)
            self.manifest["runtime"]["language"] = language
            self.check_manifest(False)

        for api in (1, 3):
            self.manifest = copy.deepcopy(original)
            self.manifest["runtime"]["api"] = api
            self.check_manifest(False)

        self.manifest = copy.deepcopy(original)
        self.manifest["runtime"]["entry"] = "main.lua"
        self.check_manifest(False)

    def test_script_source_limits(self):
        original = copy.deepcopy(self.manifest)
        for source in ("", "x" * (48 * 1024 + 1), "print('a')\x00print('b')",
                       "print('a')\x07print('b')"):
            self.manifest = copy.deepcopy(original)
            self.manifest["runtime"]["source"] = source
            self.check_manifest(False)
        self.manifest = copy.deepcopy(original)
        self.manifest["runtime"]["source"] = "print('ok')\n\tprint(\"tab\")"
        self.check_manifest(True)

    def test_runtime_permission_is_mandatory(self):
        self.manifest["permissions"] = [
            permission for permission in self.manifest["permissions"]
            if permission != "runtime.script"
        ]
        self.check_manifest(False)

    def test_unknown_permission_and_field(self):
        original = copy.deepcopy(self.manifest)
        self.manifest["permissions"].append("api.native")
        self.check_manifest(False)
        self.manifest = copy.deepcopy(original)
        self.manifest["runtime"]["binary"] = "nvngx_dlssnr.dll"
        self.check_manifest(False)
        self.manifest = copy.deepcopy(original)
        self.manifest["runtime"]["source"] = "pbs.log('info', 'ok')"
        self.check_manifest(True)

    def test_v4_manifest_cannot_declare_a_runtime(self):
        legacy = json.loads(
            (Path(__file__).resolve().parents[1] /
             "examples/stream-inspector/plugin.json").read_text(encoding="utf-8")
        )
        legacy["runtime"] = copy.deepcopy(self.manifest["runtime"])
        self.assertTrue(validate_manifest_document(json.dumps(legacy)))


if __name__ == "__main__":
    unittest.main()

"""Public compatibility examples that can be reused outside the Python SDK."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from validate import load_validator, validate_manifest_document


class ContractFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture = REPO / "tests" / "fixtures" / "manifest-contract.json"
        cls.cases = json.loads(fixture.read_text(encoding="utf-8"))["cases"]
        cls.bases = {
            "v1": json.loads((REPO / "examples/hello-world/plugin.json").read_text(encoding="utf-8")),
            "v2": json.loads((REPO / "examples/navigation-and-streaming/plugin.json").read_text(encoding="utf-8")),
            "v3": json.loads((REPO / "examples/event-notifications/plugin.json").read_text(encoding="utf-8")),
        }
        cls.validators = {
            1: load_validator(REPO / "schemas/v1/plugin.schema.json"),
            2: load_validator(REPO / "schemas/v2/plugin.schema.json"),
            3: load_validator(REPO / "schemas/v3/plugin.schema.json"),
        }

    def test_all_fixture_cases_match_expected_acceptance(self) -> None:
        self.assertGreaterEqual(len(self.cases), 15)
        names = [case["name"] for case in self.cases]
        self.assertEqual(len(names), len(set(names)), "fixture names must be unique")
        for case in self.cases:
            with self.subTest(case=case["name"]):
                manifest = copy.deepcopy(self.bases[case["base"]])
                for field in case.get("remove", []):
                    del manifest[field]
                manifest.update(copy.deepcopy(case["changes"]))
                document = json.dumps(manifest, ensure_ascii=False)
                errors = validate_manifest_document(document)
                self.assertEqual(case["accept"], not errors, errors)
                schema_errors = list(self.validators[manifest["schema"]].iter_errors(manifest))
                if case["accept"]:
                    self.assertFalse(schema_errors)
                elif case["name"] in {
                    "v2-reject-newer-api-major",
                    "v1-reject-v2-api-extension",
                    "v2-reject-leading-zero-prerelease",
                    "v1-reject-leading-zero-prerelease",
                    "v2-reject-arbitrary-navigation",
                    "v2-reject-capability-escalation",
                    "v3-reject-newer-api-major",
                    "v3-reject-unknown-event",
                    "v3-reject-missing-notification-permission",
                    "v3-reject-unexpected-notification-field",
                    "v3-reject-empty-notification-message",
                    "v3-reject-ninth-notification",
                    "v2-reject-v3-notification-field",
                    "v2-reject-v3-notification-permission",
                    "v3-reject-unknown-permission",
                }:
                    self.assertTrue(schema_errors, "schema must reject structural/API violations")
                # Semantic URL constraints such as DNS-label length and
                # provider-specific canonical paths are enforced by the CLI.


if __name__ == "__main__":
    unittest.main()

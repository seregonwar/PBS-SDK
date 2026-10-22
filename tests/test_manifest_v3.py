"""Adversarial v3 event notification and backward compatibility tests."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from validate import load_validator, validate_manifest_document


class V3NotificationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.path = REPO / "examples/event-notifications/plugin.json"
        cls.example = json.loads(cls.path.read_text(encoding="utf-8"))
        cls.v2 = json.loads((REPO / "examples/navigation-and-streaming/plugin.json").read_text(encoding="utf-8"))
        cls.v1 = json.loads((REPO / "examples/hello-world/plugin.json").read_text(encoding="utf-8"))
        cls.validator = load_validator(REPO / "schemas/v3/plugin.schema.json")

    def check(self, obj: object) -> list[str]:
        return validate_manifest_document(json.dumps(obj, ensure_ascii=False))

    def test_example_and_legacy_schemas_pass(self) -> None:
        for manifest in (self.example, self.v2, self.v1):
            with self.subTest(schema=manifest["schema"]):
                self.assertFalse(self.check(manifest))

    def test_v3_schema_major_compatibility_and_counts(self) -> None:
        self.assertEqual(3, self.validator.schema["properties"]["schema"]["const"])
        self.assertEqual(1, self.validator.schema["properties"]["api_version"]["const"])
        self.assertEqual(5, self.validator.schema["properties"]["permissions"]["maxItems"])
        self.assertEqual(8, self.validator.schema["properties"]["notifications"]["maxItems"])

    def test_api_major_not_implicitly_upgraded(self) -> None:
        for value in (0, 2, -1, 1.5, True, False, "1", None, [], {}):
            with self.subTest(api=value):
                variant = copy.deepcopy(self.example)
                variant["api_version"] = value
                self.assertNotEqual([], self.check(variant))
        variant = copy.deepcopy(self.example)
        del variant["api_version"]
        self.assertNotEqual([], self.check(variant))

    def test_unknown_schema_and_executable_root_fields_rejected(self) -> None:
        for changes in ({"schema": 4}, {"schema": "3"}, {"script": "evil.js"},
                        {"on_event": "run"}, {"api": {"major": 2}}):
            with self.subTest(changes=changes):
                variant = copy.deepcopy(self.example)
                variant.update(changes)
                self.assertNotEqual([], self.check(variant))

    def test_v1_v2_reject_v3_fields_and_permission(self) -> None:
        for original in (self.v1, self.v2):
            for field, value in (
                ("notifications", copy.deepcopy(self.example["notifications"])),
                ("permissions", original["permissions"] + ["ui.notifications"]),
            ):
                with self.subTest(schema=original["schema"], field=field):
                    variant = copy.deepcopy(original)
                    variant[field] = value
                    self.assertNotEqual([], self.check(variant))

    def test_empty_or_missing_notifications_need_no_permission(self) -> None:
        variant = copy.deepcopy(self.example)
        variant["permissions"] = []
        variant["notifications"] = []
        self.assertFalse(self.check(variant))
        del variant["notifications"]
        self.assertFalse(self.check(variant))

    def test_nonempty_notifications_need_permission(self) -> None:
        variant = copy.deepcopy(self.example)
        variant["permissions"] = []
        self.assertNotEqual([], self.check(variant))
        variant["permissions"] = ["ui.notifications"]
        self.assertFalse(self.check(variant))

    def test_exact_four_event_names(self) -> None:
        for event in ("console.connected", "console.disconnected",
                      "broadcast.started", "broadcast.stopped"):
            with self.subTest(event=event):
                variant = copy.deepcopy(self.example)
                variant["notifications"][0]["event"] = event
                self.assertFalse(self.check(variant))
        for event in ("", "console.connecting", "Console.Connected", "app.started",
                      "broadcast.error", "broadcast.stopped\n", "broadcast.started?key=x",
                      "notifications.send", "window.open", 1, None):
            with self.subTest(invalid_event=event):
                variant = copy.deepcopy(self.example)
                variant["notifications"][0]["event"] = event
                self.assertNotEqual([], self.check(variant))

    def test_required_exact_object_shape(self) -> None:
        for field in ("id", "event", "title", "message"):
            with self.subTest(required=field):
                variant = copy.deepcopy(self.example)
                del variant["notifications"][0][field]
                self.assertNotEqual([], self.check(variant))
        for extra, value in (
            ("url", "https://example.org"),
            ("webhook", "https://example.org"),
            ("command", "echo hello"),
            ("script", "eval('1')"),
            ("payload", {"token": "secret"}),
            ("native", True),
            ("context", {"console_name": "private"}),
            ("timeout", 1),
        ):
            with self.subTest(extra=extra):
                variant = copy.deepcopy(self.example)
                variant["notifications"][0][extra] = value
                self.assertNotEqual([], self.check(variant))

    def test_duplicates_and_independent_id_namespaces(self) -> None:
        variant = copy.deepcopy(self.example)
        variant["notifications"][1]["id"] = variant["notifications"][0]["id"]
        self.assertTrue(any("duplicate notification id" in e for e in self.check(variant)))
        variant = copy.deepcopy(self.example)
        shared = "same-id"
        variant["notifications"][0]["id"] = shared
        variant["cards"] = [copy.deepcopy(self.v1["cards"][0])]
        variant["cards"][0]["id"] = shared
        variant["actions"] = [copy.deepcopy(self.v2["actions"][0])]
        variant["actions"][0]["id"] = shared
        variant["presets"] = [copy.deepcopy(self.v2["presets"][0])]
        variant["presets"][0]["id"] = shared
        variant["permissions"] = ["ui.cards", "links.open", "ui.actions",
                                  "stream.presets", "ui.notifications"]
        self.assertFalse(self.check(variant))

    def test_max_eight_notification_entries(self) -> None:
        variant = copy.deepcopy(self.example)
        variant["notifications"] = [
            {"id": f"item-{i}", "event": "console.connected", "title": "Title", "message": "Message"}
            for i in range(8)
        ]
        self.assertFalse(self.check(variant))
        variant["notifications"].append(
            {"id": "item-8", "event": "console.connected", "title": "Title", "message": "Message"})
        self.assertNotEqual([], self.check(variant))

    def test_invalid_notification_ids(self) -> None:
        for value in ("", "-foo", "foo-", "a..b", "a--b", "Upper", "a/b",
                      "a_b", "a b", "é", "a" * 65):
            with self.subTest(id=value):
                variant = copy.deepcopy(self.example)
                variant["notifications"][0]["id"] = value
                self.assertNotEqual([], self.check(variant))

    def test_text_nonempty_utf8_byte_limits_and_controls(self) -> None:
        for field, limit in (("title", 96), ("message", 240)):
            for value, expected_valid in (
                ("", False),
                ("X" * limit, True),
                ("X" * (limit + 1), False),
                ("é" * (limit // 2), True),
                ("é" * (limit // 2 + 1), False),
                ("line\nbreak", False),
                ("\t", False),
                ("\x00", False),
                ("\x7f", False),
                (123, False),
                ([], False),
            ):
                with self.subTest(field=field, length=len(str(value)), valid=expected_valid):
                    variant = copy.deepcopy(self.example)
                    variant["notifications"][0][field] = value
                    self.assertEqual(expected_valid, not self.check(variant))

    def test_literal_markup_and_dollar_braces_have_no_interpolation(self) -> None:
        variant = copy.deepcopy(self.example)
        variant["notifications"][0]["title"] = "{console} $value %s"
        variant["notifications"][0]["message"] = "<script>alert(1)</script>"
        self.assertFalse(self.check(variant))

    def test_v2_capabilities_work_unchanged_in_v3(self) -> None:
        variant = copy.deepcopy(self.v2)
        variant.update({"schema": 3, "api_version": 1})
        self.assertFalse(self.check(variant))
        variant["permissions"].append("ui.notifications")
        variant["notifications"] = [copy.deepcopy(self.example["notifications"][0])]
        self.assertFalse(self.check(variant))

    def test_max_five_distinct_permissions(self) -> None:
        variant = copy.deepcopy(self.example)
        variant["permissions"] = [
            "ui.cards", "links.open", "ui.actions", "stream.presets", "ui.notifications"
        ]
        self.assertFalse(self.check(variant))
        variant["permissions"].append("ui.notifications")
        self.assertNotEqual([], self.check(variant))

    def test_duplicate_json_keys_rejected(self) -> None:
        raw = json.dumps(self.example)
        self.assertTrue(any("duplicate JSON key" in e for e in validate_manifest_document(
            raw.replace('"schema": 3,', '"schema": 3, "schema": 3,', 1))))
        self.assertTrue(any("duplicate JSON key" in e for e in validate_manifest_document(
            raw.replace('"event": "console.connected"', '"event": "console.connected", "event": "broadcast.started"', 1))))

    def test_cli_accepts_three_versions_and_rejects_bad_event(self) -> None:
        command = [sys.executable, str(REPO / "scripts/validate.py")]
        good = subprocess.run([
            *command, str(REPO / "examples/hello-world/plugin.json"),
            str(REPO / "examples/navigation-and-streaming/plugin.json"), str(self.path)
        ], capture_output=True, text=True)
        self.assertEqual(0, good.returncode, good.stderr)
        self.assertEqual(3, good.stdout.count("PASS"))
        with tempfile.TemporaryDirectory(dir=REPO / "tests") as directory:
            bad_path = Path(directory) / "bad.json"
            bad = copy.deepcopy(self.example)
            bad["notifications"][0]["event"] = "app.started"
            bad_path.write_text(json.dumps(bad), encoding="utf-8")
            result = subprocess.run([*command, str(bad_path)], capture_output=True, text=True)
            self.assertEqual(1, result.returncode)
            self.assertIn("FAIL", result.stderr)


if __name__ == "__main__":
    unittest.main()

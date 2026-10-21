"""Regression and adversarial tests for the public declarative plugin format."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from validate import load_validator, parse_json_document, validate_manifest_document


class PluginManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = load_validator()
        cls.example_path = REPO_ROOT / "examples" / "hello-world" / "plugin.json"
        cls.example = parse_json_document(cls.example_path.read_text(encoding="utf-8"))

    def check(self, manifest: object) -> list[str]:
        return validate_manifest_document(json.dumps(manifest), self.validator)

    def test_example_passes(self) -> None:
        self.assertEqual([], self.check(self.example))

    def test_schema_is_valid_draft_2020_12(self) -> None:
        self.assertEqual(
            "https://json-schema.org/draft/2020-12/schema",
            self.validator.schema["$schema"],
        )
        self.assertEqual(1, self.validator.schema["properties"]["schema"]["const"])

    def test_minimum_manifest_without_cards_passes(self) -> None:
        manifest = copy.deepcopy(self.example)
        manifest["cards"] = []
        manifest["permissions"] = []
        self.assertEqual([], self.check(manifest))

    def test_independent_plugin_and_manifest_versions(self) -> None:
        for version in ("0.0.0", "1.0.0", "12.4.103", "2.0.0-beta.1", "3.5.8+build.7"):
            with self.subTest(version=version):
                manifest = copy.deepcopy(self.example)
                manifest["version"] = version
                self.assertEqual([], self.check(manifest))

    def test_allowed_https_urls(self) -> None:
        for url in (
            "https://example.com",
            "https://example.com/path?hello=world#section",
            "https://example.com:443/docs",
            "https://sub.example.org/a%20b",
            "https://localhost/",
        ):
            with self.subTest(url=url):
                manifest = copy.deepcopy(self.example)
                manifest["cards"][0]["url"] = url
                self.assertEqual([], self.check(manifest))

    def test_multiple_cards_with_distinct_ids(self) -> None:
        manifest = copy.deepcopy(self.example)
        second_card = copy.deepcopy(manifest["cards"][0])
        second_card["id"] = "changelog"
        manifest["cards"].append(second_card)
        self.assertEqual([], self.check(manifest))

    def test_all_top_level_fields_are_required(self) -> None:
        for key in self.example:
            with self.subTest(key=key):
                manifest = copy.deepcopy(self.example)
                del manifest[key]
                self.assertNotEqual([], self.check(manifest))

    def test_all_card_fields_are_required(self) -> None:
        for key in self.example["cards"][0]:
            with self.subTest(key=key):
                manifest = copy.deepcopy(self.example)
                del manifest["cards"][0][key]
                self.assertNotEqual([], self.check(manifest))

    def test_forbidden_top_level_fields(self) -> None:
        for key, value in (
            ("enabled", True),
            ("entrypoint", "./plugin.js"),
            ("scripts", ["./setup.sh"]),
            ("onStartup", "run()"),
            ("network", True),
            ("filesystem", "/"),
            ("dependencies", ["native-library"]),
            ("executable", "plugin.dll"),
            ("__proto__", {}),
        ):
            with self.subTest(key=key):
                manifest = copy.deepcopy(self.example)
                manifest[key] = value
                self.assertNotEqual([], self.check(manifest))

    def test_forbidden_card_fields(self) -> None:
        for key, value in (
            ("html", "<script>alert(1)</script>"),
            ("javascript", "alert(1)"),
            ("onclick", "run()"),
            ("command", "rm -rf /"),
            ("target", "_blank"),
            ("headers", {"Authorization": "Bearer something"}),
        ):
            with self.subTest(key=key):
                manifest = copy.deepcopy(self.example)
                manifest["cards"][0][key] = value
                self.assertNotEqual([], self.check(manifest))

    def test_rejects_non_https_and_unsafe_urls(self) -> None:
        unsafe_urls = (
            "http://example.com",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "file:///etc/passwd",
            "ftp://example.com/plugin",
            "//example.com",
            "example.com/no-scheme",
            "HTTPS://example.com",
            "https:///missing-host",
            "https://",
            "https://user@example.com/path",
            "https://user:pass@example.com",
            "https://example.com:invalid/",
            "https://example.com:99999/",
            "https://example.com:0/",
            "https://example.com:000001/",
            "https://[::1]/",
            "https://host..example.com/",
            "https://éxample.com/",
            "https://example.com/é",
            "https://example.com/has whitespace",
            "https://example.com/\nnewline",
            "https://example.com/\ttab",
            "https://example.com/\u007fdel",
            "https://example.com\\evil.com",
        )
        for url in unsafe_urls:
            with self.subTest(url=url):
                manifest = copy.deepcopy(self.example)
                manifest["cards"][0]["url"] = url
                self.assertNotEqual([], self.check(manifest))

    def test_rejects_unknown_or_missing_permissions(self) -> None:
        for permissions in (
            [],
            ["ui.cards"],
            ["links.open"],
            ["ui.cards", "ui.cards", "links.open"],
            ["ui.cards", "links.open", "code.execute"],
            ["ui.cards", "links.open", "filesystem.read"],
            ["ui.cards", 123],
            "ui.cards",
        ):
            with self.subTest(permissions=permissions):
                manifest = copy.deepcopy(self.example)
                manifest["permissions"] = permissions
                self.assertNotEqual([], self.check(manifest))

    def test_invalid_identifiers(self) -> None:
        invalid_plugin_ids = (
            "",
            "X",
            "UPPER.case",
            "../escape",
            "com..example",
            ".example",
            "example.",
            "com/example",
            "with space",
            "plugin_name",
            "☃.unicode",
            "com.example\n",
            "a" * 65,
        )
        for plugin_id in invalid_plugin_ids:
            with self.subTest(plugin_id=plugin_id):
                manifest = copy.deepcopy(self.example)
                manifest["id"] = plugin_id
                self.assertNotEqual([], self.check(manifest))
        invalid_card_ids = ("", "../escape", ".relative", "camelCase", "has space", "c_name", "☃", "card\n", "a" * 65)
        for card_id in invalid_card_ids:
            with self.subTest(card_id=card_id):
                manifest = copy.deepcopy(self.example)
                manifest["cards"][0]["id"] = card_id
                self.assertNotEqual([], self.check(manifest))

    def test_invalid_version_numbers(self) -> None:
        for version in (
            "", "1", "1.0", "v1.0.0", "01.2.3", "1.02.3",
            "1.0.0.0", "1.0.0-..beta", "1.0.0\n", "1.0.0\nextra"
        ):
            with self.subTest(version=version):
                manifest = copy.deepcopy(self.example)
                manifest["version"] = version
                self.assertNotEqual([], self.check(manifest))

    def test_bad_types_and_limits(self) -> None:
        for key, value in (
            ("schema", "1"),
            ("schema", 2),
            ("schema", True),
            ("schema", None),
            ("name", ""),
            ("name", "X" * 97),
            ("description", "X" * 513),
            ("author", ""),
            ("author", "X" * 97),
            ("cards", {}),
            ("cards", [copy.deepcopy(self.example["cards"][0])] * 17),
            ("id", ["untrusted"]),
        ):
            with self.subTest(field=key, value=str(value)[:30]):
                manifest = copy.deepcopy(self.example)
                manifest[key] = value
                self.assertNotEqual([], self.check(manifest))

    def test_rejects_duplicate_card_ids(self) -> None:
        manifest = copy.deepcopy(self.example)
        manifest["cards"].append(copy.deepcopy(manifest["cards"][0]))
        manifest["cards"][1]["title"] = "Different card with reused ID"
        self.assertTrue(any("duplicate card id" in msg for msg in self.check(manifest)))

    def test_rejects_duplicate_json_object_keys(self) -> None:
        duplicates = (
            '{"schema":1,"schema":1}',
            '{"foo":1,"foo":2}',
            '{"cards":[{"id":"first","id":"second"}]}',
        )
        for document in duplicates:
            with self.subTest(document=document):
                errors = validate_manifest_document(document, self.validator)
                self.assertTrue(any("duplicate JSON key" in msg for msg in errors))

    def test_rejects_nonstandard_or_malformed_json(self) -> None:
        for document in (
            "",
            "{",
            "[]",
            "null",
            '{"schema": NaN}',
            '{"schema": Infinity}',
            '{"schema":1,}',
            '{"schema":1} trailing',
        ):
            with self.subTest(document=document):
                self.assertNotEqual([], validate_manifest_document(document, self.validator))

    def test_rejects_bare_root_and_scalar_types(self) -> None:
        for root in ([], None, 1, True, "plugin"):
            with self.subTest(root=root):
                self.assertNotEqual([], self.check(root))

    def test_single_digit_and_dotted_card_ids_are_valid(self) -> None:
        manifest = copy.deepcopy(self.example)
        manifest["id"] = "3"
        manifest["cards"][0]["id"] = "1.docs"
        self.assertEqual([], self.check(manifest))

    def test_rejects_ascii_control_text_and_excess_utf8_bytes(self) -> None:
        for field in ("name", "description", "author"):
            with self.subTest(field=field):
                manifest = copy.deepcopy(self.example)
                manifest[field] = "line\nfeed"
                self.assertNotEqual([], self.check(manifest))
        for field in ("title", "description", "button_label"):
            with self.subTest(field=field):
                manifest = copy.deepcopy(self.example)
                manifest["cards"][0][field] = "tab\tin text"
                self.assertNotEqual([], self.check(manifest))

        manifest = copy.deepcopy(self.example)
        manifest["name"] = "é" * 60  # 60 Unicode characters, 120 UTF-8 bytes
        self.assertNotEqual([], self.check(manifest))

    def test_rejects_oversized_manifest_even_with_valid_json(self) -> None:
        document = json.dumps(self.example) + " " * 70_000
        errors = validate_manifest_document(document, self.validator)
        self.assertTrue(any("65536" in message for message in errors))

    def test_links_are_inert_plain_text(self) -> None:
        # Content may contain punctuation, angle brackets, and quotes. The app
        # is responsible for displaying these as untrusted text, not HTML.
        manifest = copy.deepcopy(self.example)
        manifest["cards"][0]["description"] = "<img src=x onerror=alert(1)>"
        manifest["cards"][0]["title"] = "\"'><script>alert(1)</script>"
        self.assertEqual([], self.check(manifest))

    def test_cli_reports_success_and_failure(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests") as directory:
            invalid_path = Path(directory) / "invalid.json"
            invalid_path.write_text('{"schema": 1, "code": "run-me"}', encoding="utf-8")
            command = [sys.executable, str(REPO_ROOT / "scripts" / "validate.py")]

            good = subprocess.run(
                [*command, str(self.example_path)], text=True, capture_output=True
            )
            self.assertEqual(0, good.returncode, good.stderr)
            self.assertIn("PASS", good.stdout)

            bad = subprocess.run([*command, str(invalid_path)], text=True, capture_output=True)
            self.assertEqual(1, bad.returncode)
            self.assertIn("FAIL", bad.stderr)


if __name__ == "__main__":
    unittest.main()

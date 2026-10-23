"""V2 API compatibility, capability review, and hostile manifest regression tests."""

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
from validate import load_validator, validate_manifest_document


class V2ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.example_path = REPO_ROOT / "examples" / "navigation-and-streaming" / "plugin.json"
        cls.legacy_path = REPO_ROOT / "examples" / "hello-world" / "plugin.json"
        cls.example = json.loads(cls.example_path.read_text(encoding="utf-8"))
        cls.legacy = json.loads(cls.legacy_path.read_text(encoding="utf-8"))
        cls.validator_v2 = load_validator(REPO_ROOT / "schemas" / "v2" / "plugin.schema.json")
        cls.validator_v1 = load_validator(REPO_ROOT / "schemas" / "v1" / "plugin.schema.json")

    def check(self, manifest: object) -> list[str]:
        return validate_manifest_document(json.dumps(manifest))

    def test_v2_example_and_v1_example_are_both_accepted(self) -> None:
        self.assertEqual([], self.check(self.example))
        self.assertEqual([], self.check(self.legacy))

    def test_explicit_schema_validators_preserve_v1_and_v2(self) -> None:
        self.assertEqual([], validate_manifest_document(json.dumps(self.legacy), self.validator_v1))
        self.assertEqual([], validate_manifest_document(json.dumps(self.example), self.validator_v2))
        self.assertNotEqual([], validate_manifest_document(json.dumps(self.example), self.validator_v1))
        self.assertNotEqual([], validate_manifest_document(json.dumps(self.legacy), self.validator_v2))

    def test_v2_schema_declares_v2_and_api_version_one(self) -> None:
        self.assertEqual(2, self.validator_v2.schema["properties"]["schema"]["const"])
        self.assertEqual(1, self.validator_v2.schema["properties"]["api_version"]["const"])

    def test_v1_rejects_v2_fields(self) -> None:
        for key, value in (
            ("api_version", 1),
            ("actions", []),
            ("presets", []),
        ):
            with self.subTest(key=key):
                variant = copy.deepcopy(self.legacy)
                variant[key] = value
                self.assertNotEqual([], self.check(variant))

    def test_v2_api_version_compatibility_is_checked(self) -> None:
        for api_version in (None, 0, 2, 3, -1, "1", True, 1.5, [], {}):
            with self.subTest(api_version=api_version):
                variant = copy.deepcopy(self.example)
                if api_version is None:
                    del variant["api_version"]
                else:
                    variant["api_version"] = api_version
                errors = self.check(variant)
                self.assertNotEqual([], errors)
                self.assertTrue(any("API version" in error for error in errors), errors)

    def test_unknown_or_future_manifest_schemas_are_rejected(self) -> None:
        for schema in (0, 5, 100, "2", 2.0, True, None):
            with self.subTest(schema=schema):
                variant = copy.deepcopy(self.example)
                variant["schema"] = schema
                self.assertNotEqual([], self.check(variant))

    def test_all_four_navigation_actions_are_allowed(self) -> None:
        for page in ("consoles", "playback", "streaming", "appearance"):
            with self.subTest(page=page):
                variant = copy.deepcopy(self.example)
                variant["actions"][0]["target"] = f"open.settings.{page}"
                self.assertEqual([], self.check(variant))

    def test_navigation_actions_are_strictly_allowlisted(self) -> None:
        for target in (
            "open.settings",
            "open.settings.licenses",
            "open.settings.accounts",
            "open.settings.security",
            "open.settings.plugins",
            "open.settings.backups",
            "open.streaming.start",
            "open.settings.consoles/../../secret",
            "open.settings.consoles?admin=true",
            "open.settings.appearance\n",
            "app://settings/consoles",
            "javascript:alert(1)",
            "file:///C:/Windows",
            "shell:run",
            "cmd.exe",
            "open.settings.Consoles",
            "",
            1,
        ):
            with self.subTest(target=target):
                variant = copy.deepcopy(self.example)
                variant["actions"][0]["target"] = target
                self.assertNotEqual([], self.check(variant))

    def test_actions_need_ui_actions_permission(self) -> None:
        variant = copy.deepcopy(self.example)
        variant["permissions"].remove("ui.actions")
        self.assertNotEqual([], self.check(variant))
        variant["actions"] = []
        self.assertEqual([], self.check(variant))

    def test_presets_need_presets_permission(self) -> None:
        variant = copy.deepcopy(self.example)
        variant["permissions"].remove("stream.presets")
        self.assertNotEqual([], self.check(variant))
        variant["presets"] = []
        self.assertEqual([], self.check(variant))

    def test_actions_and_presets_optional_without_permissions(self) -> None:
        variant = copy.deepcopy(self.example)
        variant["actions"] = []
        variant["presets"] = []
        variant["permissions"] = []
        self.assertEqual([], self.check(variant))
        del variant["actions"]
        del variant["presets"]
        self.assertEqual([], self.check(variant))
        del variant["cards"]
        self.assertEqual([], self.check(variant))

    def test_v2_cards_follow_v1_permissions_rule(self) -> None:
        variant = copy.deepcopy(self.example)
        variant["cards"] = [copy.deepcopy(self.legacy["cards"][0])]
        self.assertNotEqual([], self.check(variant))
        variant["permissions"].extend(["ui.cards", "links.open"])
        self.assertEqual([], self.check(variant))
        variant["permissions"].remove("links.open")
        self.assertNotEqual([], self.check(variant))

    def test_duplicates_are_rejected_per_collection(self) -> None:
        for key in ("actions", "presets"):
            with self.subTest(collection=key):
                variant = copy.deepcopy(self.example)
                variant[key].append(copy.deepcopy(variant[key][0]))
                variant[key][-1]["label" if key == "actions" else "name"] = "Second item"
                errors = self.check(variant)
                self.assertTrue(any("duplicate" in error for error in errors), errors)

    def test_unsupported_permission_or_duplicates_are_rejected(self) -> None:
        for permissions in (
            ["ui.actions", "stream.presets", "filesystem.read"],
            ["ui.actions", "ui.actions", "stream.presets"],
            ["ui.actions", "stream.presets", "shell.execute"],
            "ui.actions",
        ):
            with self.subTest(permissions=permissions):
                variant = copy.deepcopy(self.example)
                variant["permissions"] = permissions
                self.assertNotEqual([], self.check(variant))

    def test_unexpected_executable_or_sensitive_fields_rejected(self) -> None:
        hostile = {
            "entrypoint": "plugin.dll",
            "code": "fetch('https://example.com')",
            "javascript": "eval('1')",
            "script": "system('id')",
            "webhook": "https://example.com",
            "headers": {"Authorization": "Bearer SECRET"},
            "credentials": {"stream_key": "SECRET"},
            "stream_key": "SECRET",
            "token": "SECRET",
            "native": True,
            "filesystem": "/",
            "api": {"major": 999},
            "enabled": True,
            "update_url": "https://example.com/download.exe",
        }
        for key, value in hostile.items():
            with self.subTest(field=key):
                variant = copy.deepcopy(self.example)
                variant[key] = value
                self.assertNotEqual([], self.check(variant))

    def test_actions_and_presets_reject_unknown_members(self) -> None:
        for collection in ("actions", "presets"):
            for key, value in (
                ("on_click", "fetch('https://example.com')"),
                ("args", ["--privileged"]),
                ("script", "run"),
                ("credentials", "SECRET"),
                ("key", "SECRET"),
                ("request_headers", {"Authorization": "Basic secret"}),
            ):
                with self.subTest(collection=collection, key=key):
                    variant = copy.deepcopy(self.example)
                    variant[collection][0][key] = value
                    self.assertNotEqual([], self.check(variant))

    def test_required_action_and_preset_members(self) -> None:
        for collection in ("actions", "presets"):
            for key in self.example[collection][0]:
                with self.subTest(collection=collection, key=key):
                    variant = copy.deepcopy(self.example)
                    del variant[collection][0][key]
                    self.assertNotEqual([], self.check(variant))

    def test_only_rtmps_ingest_endpoints_without_credentials_are_accepted(self) -> None:
        for url in (
            "rtmps://ingest.example.com/live",
            "rtmps://ingest.example.com:443/app",
            "rtmps://sub.example.org:1935/ingest",
            "rtmps://ingest.example.com/ingest/custom",
            "rtmps://ingest.example.com/app/live~primary",
            "rtmps://live.twitch.tv/app",
            "rtmps://a.rtmps.youtube.com/live2",
        ):
            with self.subTest(url=url):
                variant = copy.deepcopy(self.example)
                variant["presets"][0]["url"] = url
                self.assertEqual([], self.check(variant))

    def test_rtmps_path_and_dns_label_length_boundaries(self) -> None:
        # Native parser measures the path *after* its initial slash.
        # DNS label width is limited to 63 ASCII bytes, per RFC 1035.
        accepted = (
            "rtmps://ingest.example.org/" + "a" * 96,
            "rtmps://" + "a" * 63 + ".example.org/live",
            "rtmps://ingest.example.org:00001/live",
        )
        rejected = (
            "rtmps://ingest.example.org/" + "a" * 97,
            "rtmps://" + "a" * 64 + ".example.org/live",
            "rtmps://ingest.example.org:000001/live",
            "rtmps://ingest.example.org/segment/..",
            "rtmps://ingest.example.org/segment/.",
        )
        for valid, cases in ((True, accepted), (False, rejected)):
            for url in cases:
                with self.subTest(url=url, valid=valid):
                    variant = copy.deepcopy(self.example)
                    variant["presets"][0]["url"] = url
                    self.assertEqual(valid, not self.check(variant))

    def test_numeric_prerelease_requires_no_leading_zero(self) -> None:
        for valid, versions in (
            (True, ("1.2.3-0", "1.2.3-10", "1.2.3-alpha.0", "1.2.3+build.01", "1.2.3-alpha01")),
            (False, ("1.2.3-00", "1.2.3-01", "1.2.3-alpha.002", "1.2.3-001+build.1")),
        ):
            for version in versions:
                with self.subTest(version=version, valid=valid):
                    variant = copy.deepcopy(self.example)
                    variant["version"] = version
                    self.assertEqual(valid, not self.check(variant))
                    self.assertEqual(
                        valid,
                        self.validator_v2.is_valid(variant),
                        "v2 schema and CLI must agree on SemVer",
                    )

    def test_rejects_excessively_nested_json_without_crashing(self) -> None:
        document = "[" * 1500 + "0" + "]" * 1500
        errors = validate_manifest_document(document)
        self.assertNotEqual([], errors)
        # Python's JSON decoder accepts different nesting depths across
        # distributions; either a decode error or a non-object-root rejection
        # is the correct fail-closed behavior.
        self.assertTrue(
            "invalid JSON" in errors[0] or "manifest must be a JSON object" in errors[0],
            errors,
        )

    def test_dangerous_or_secret_bearing_stream_urls_are_denied(self) -> None:
        for url in (
            "rtmp://ingest.example.com/live",
            "https://ingest.example.com/live",
            "ftp://ingest.example.com/live",
            "RTMPS://ingest.example.com/live",
            "rtmps://",
            "rtmps:///live",
            "rtmps://user@ingest.example.com/live",
            "rtmps://user:password@ingest.example.com/live",
            "rtmps://ingest.example.com/live?key=SECRET",
            "rtmps://ingest.example.com/live?",
            "rtmps://ingest.example.com/live#SECRET",
            "rtmps://ingest.example.com/live#",
            "rtmps://ingest.example.com/live//stream",
            "rtmps://ingest.example.com/live/./stream",
            "rtmps://ingest.example.com/live/../stream",
            "rtmps://ingest.example.com/live/",
            "rtmps://ingest.example.com/app/{stream_key}",
            "rtmps://ingest.example.com/app?token=SECRET",
            "rtmps://ingest.example.com/",
            "rtmps://ingest.example.com",
            "rtmps://127.0.0.1/live?token=secret",
            "rtmps://127.0.0.1/live",
            "rtmps://999.999/live",
            "rtmps://localhost/stream",
            "rtmps://fake.local/live",
            "rtmps://ingest.home.arpa/live",
            "rtmps://server.lan/live",
            "rtmps://server.internal/live",
            "rtmps://live.twitch.tv/live",
            "rtmps://a.rtmps.youtube.com/app",
            "rtmps://[::1]/live",
            "rtmps://ingest..example.com/live",
            "rtmps://ingest.example.com:0/live",
            "rtmps://ingest.example.com:99999/live",
            "rtmps://ingest.example.com:123456/live",
            "rtmps://ingest.example.com:abc/live",
            "rtmps://ingest.example.com\\@evil.example/live",
            "rtmps://ingest.example.com/live\nsecret",
            "rtmps://ingest.example.com/livé",
            "rtmps://ingest.example.com/live%2FSECRET",
            "",
        ):
            with self.subTest(url=url):
                variant = copy.deepcopy(self.example)
                variant["presets"][0]["url"] = url
                self.assertNotEqual([], self.check(variant))

    def test_limit_enforcement_for_actions_and_presets(self) -> None:
        for collection in ("actions", "presets"):
            variant = copy.deepcopy(self.example)
            variant[collection] = []
            max_items = 16 if collection == "actions" else 8
            for index in range(max_items):
                item = copy.deepcopy(self.example[collection][0])
                item["id"] = f"item-{index}"
                variant[collection].append(item)
            self.assertEqual([], self.check(variant))
            variant[collection].append(copy.deepcopy(self.example[collection][0]))
            self.assertNotEqual([], self.check(variant))

    def test_rejects_untrusted_text_controls_and_oversized_utf8(self) -> None:
        for collection, key in (
            ("actions", "label"),
            ("actions", "description"),
            ("presets", "name"),
        ):
            variant = copy.deepcopy(self.example)
            variant[collection][0][key] = "line\nfeed"
            self.assertNotEqual([], self.check(variant))
            variant[collection][0][key] = "é" * (300 if key == "description" else 50)
            self.assertNotEqual([], self.check(variant))

    def test_invalid_json_and_duplicate_keys_rejected_in_v2(self) -> None:
        for document in (
            '{"schema":2,"schema":2,"api_version":1}',
            '{"schema":2,"api_version":1,"api_version":2}',
            '{"schema":2,"api_version":1,"actions":[{"id":"a","id":"b"}]}',
            '{"schema":2,"api_version":NaN}',
            '{"schema":2,"api_version":1,}',
        ):
            with self.subTest(document=document):
                self.assertNotEqual([], validate_manifest_document(document))

    def test_cli_validates_mixed_versions_and_fails_invalid(self) -> None:
        command = [sys.executable, str(REPO_ROOT / "scripts" / "validate.py")]
        good = subprocess.run(
            [*command, str(self.legacy_path), str(self.example_path)],
            capture_output=True, text=True
        )
        self.assertEqual(0, good.returncode, good.stderr)
        self.assertEqual(2, good.stdout.count("PASS"))

        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "tests") as temp_dir:
            path = Path(temp_dir) / "future-api.json"
            future_api = copy.deepcopy(self.example)
            future_api["api_version"] = 999
            path.write_text(json.dumps(future_api), encoding="utf-8")
            bad = subprocess.run(
                [*command, str(self.legacy_path), str(path)],
                capture_output=True, text=True
            )
            self.assertEqual(1, bad.returncode)
            self.assertIn("PASS", bad.stdout)
            self.assertIn("incompatible API version", bad.stderr)


if __name__ == "__main__":
    unittest.main()

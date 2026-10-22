"""Executable developer source produces the same strict host manifests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pbs_sdk import Plugin, HostEvent, SettingsPage, ManifestError
from scripts.validate import validate_manifest_document

SOURCE = ROOT / "examples/creator-workflow/build.py"
spec = importlib.util.spec_from_file_location("creator_workflow", SOURCE)
assert spec and spec.loader
authoring = importlib.util.module_from_spec(spec)
spec.loader.exec_module(authoring)


class CodeFirstTests(unittest.TestCase):
    def test_production_workflow_is_host_compatible(self):
        plugin = authoring.creator_workflow()
        manifest = plugin.manifest()
        self.assertEqual("dev.example.creator-workflow", manifest["id"])
        self.assertEqual(3, manifest["schema"])
        self.assertEqual(["ui.cards", "links.open", "ui.actions", "stream.presets",
                          "ui.notifications"], manifest["permissions"])
        self.assertEqual((2, 2, 2, 4), tuple(len(manifest[key])
                         for key in ("cards", "actions", "presets", "notifications")))
        self.assertEqual([], validate_manifest_document(plugin.render()))

    def test_profiles_are_actual_authoring_logic(self):
        manifest = authoring.creator_workflow(platforms=("twitch",), profile="quick").manifest()
        self.assertEqual(["ingest-twitch"], [item["id"] for item in manifest["presets"]])
        self.assertEqual(3, len(manifest["notifications"]))
        self.assertEqual([], validate_manifest_document(json.dumps(manifest)))
        with self.assertRaisesRegex(ValueError, "unknown platforms"):
            authoring.creator_workflow(platforms=("unknown",))
        with self.assertRaisesRegex(ValueError, "non-duplicated"):
            authoring.creator_workflow(platforms=("twitch", "twitch"))

    def test_build_is_reproducible_and_rejects_invalid_before_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "dist/plugin.json"
            plugin = authoring.creator_workflow()
            plugin.build(target)
            initial = target.read_bytes()
            self.assertEqual(initial, plugin.render().encode("utf-8"))
            plugin.build(target)
            self.assertEqual(initial, target.read_bytes())
            unsafe = authoring.creator_workflow()
            unsafe.stream_preset("invalid", name="Unsafe", url="rtmp://127.0.0.1/live")
            with self.assertRaises(ManifestError):
                unsafe.build(target)
            self.assertEqual(initial, target.read_bytes())

    def test_permissions_are_inferred_without_hidden_grants(self):
        def fresh():
            return Plugin("example.test", "Test", "1.0.0", "Summary", "Author")
        self.assertEqual([], fresh().manifest()["permissions"])
        self.assertEqual(["ui.notifications"], fresh().on(
            HostEvent.CONSOLE_CONNECTED, id="notice", title="Hi", message="Connected"
        ).manifest()["permissions"])
        self.assertEqual(["ui.actions"], fresh().shortcut(
            "go", label="Settings", description="View", target=SettingsPage.STREAMING
        ).manifest()["permissions"])
        self.assertEqual(["ui.cards", "links.open"], fresh().card(
            "docs", title="Guide", description="Help", button_label="Open",
            url="https://example.org/docs").manifest()["permissions"])

    def test_output_is_a_copy_and_builder_validates_rule_namespace(self):
        builder = authoring.creator_workflow()
        document = builder.manifest()
        document["presets"][0]["url"] = "rtmp://127.0.0.1/live"
        document["permissions"].clear()
        self.assertEqual([], validate_manifest_document(builder.render()))
        builder.on(HostEvent.CONSOLE_CONNECTED, id="preflight", title="Duplicate", message="No")
        with self.assertRaisesRegex(ManifestError, "duplicate notification id"):
            builder.render()
        with self.assertRaises(ValueError):
            authoring.creator_workflow().on("app.exec", id="danger", title="No", message="No")

    def test_cli_build_and_preview_are_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "creator.json"
            result = subprocess.run(
                [sys.executable, "-B", str(SOURCE), "--profile", "quick",
                 "--platform", "youtube", "--output", str(output),
                 "--demo-event", "broadcast.started"], capture_output=True, text=True,
                check=False, timeout=25,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("Authoring preview:", result.stdout)
            manifest = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("ingest-youtube", manifest["presets"][0]["id"])
            self.assertEqual([], validate_manifest_document(output.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()

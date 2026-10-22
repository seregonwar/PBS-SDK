#!/usr/bin/env python3
"""Creator Workflow: an actual, configurable plugin authored in Python.

Run on the DEVELOPER machine. PBS Studio installs only the generated manifest,
and does not import/interpret this file or execute this Python code.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

SDK_ROOT = Path(__file__).resolve().parents[2]
if str(SDK_ROOT) not in sys.path:
    sys.path.insert(0, str(SDK_ROOT))
# The SDK can be checked out on junctions/network-backed Windows drives. An
# authoring CLI does not need .pyc writes; avoid filesystem stalls there.
if sys.platform == "win32":
    sys.dont_write_bytecode = True

from pbs_sdk import HostEvent, Plugin, SettingsPage


PLATFORMS = {
    "twitch": ("Twitch", "rtmps://live.twitch.tv/app"),
    "youtube": ("YouTube", "rtmps://a.rtmps.youtube.com/live2"),
}


def creator_workflow(*, platforms: tuple[str, ...] = ("twitch", "youtube"),
                     profile: str = "production") -> Plugin:
    """Build a set of production broadcast workflows from real Python logic.

    Profiles and platform choices are evaluated when the author builds the
    package, not whenever viewers connect or the host receives an event.
    """
    if profile not in {"production", "quick"}:
        raise ValueError("profile must be 'production' or 'quick'")
    if not platforms or len(platforms) != len(set(platforms)):
        raise ValueError("select at least one non-duplicated streaming platform")
    if unknown := set(platforms) - PLATFORMS.keys():
        raise ValueError(f"unknown platforms: {', '.join(sorted(unknown))}")

    plugin = Plugin(
        id="dev.example.creator-workflow",
        name="Creator Workflow Companion",
        version="1.0.0",
        author="PBS-SDK contributors",
        description=("Operator runbook, stream destination templates and "
                     "safe on-screen broadcast reminders for PBS Studio."),
    )
    # Card links are HTTPS and only open after a user click and a fresh grant
    # check. No stream keys, access tokens or browser automation are supplied.
    plugin.card(
        "stream-runbook", title="Before you go live",
        description="Review your console picture, audio levels and stream privacy.",
        button_label="Open operator guide",
        url="https://github.com/seregonwar/PBS-SDK/blob/main/examples/creator-workflow/RUNBOOK.md",
    )
    plugin.card(
        "security-guide", title="Protect your stream key",
        description="PBS requires your own key inside the protected stream editor.",
        button_label="Review plugin security",
        url="https://github.com/seregonwar/PBS-SDK/blob/main/docs/security.md",
    )
    plugin.shortcut(
        "streaming-settings", label="Open streaming controls",
        description="Review destinations before starting the broadcast.",
        target=SettingsPage.STREAMING,
    )
    plugin.shortcut(
        "playback-settings", label="Check playback latency",
        description="Review picture and latency settings.",
        target=SettingsPage.PLAYBACK,
    )
    for platform in platforms:
        name, ingest = PLATFORMS[platform]
        plugin.stream_preset(f"ingest-{platform}", name=f"{name} (manual key)",
                             url=ingest)

    plugin.on(
        HostEvent.CONSOLE_CONNECTED, id="preflight",
        title="Console connected — preflight",
        message="Check video and audio before opening your streaming dashboard.",
    )
    plugin.on(
        HostEvent.BROADCAST_STARTED, id="live-check",
        title="Broadcast live — verify your output",
        message="Check your dashboard for audio sync, connection quality and privacy.",
    )
    plugin.on(
        HostEvent.BROADCAST_STOPPED, id="wrap-up",
        title="Broadcast ended — wrap up",
        message="Review the recording, timestamps and any dropped-frame warnings.",
    )
    if profile == "production":
        plugin.on(
            HostEvent.CONSOLE_DISCONNECTED, id="signal-loss",
            title="Console disconnected",
            message="Inspect the console connection before resuming your broadcast.",
        )
    return plugin


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("production", "quick"),
                        default="production", help="Which operator runbook to generate")
    parser.add_argument("--platform", choices=tuple(PLATFORMS),
                        action="append", dest="platforms", help="Repeat for each destination")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).with_name("dist") / "plugin.json")
    parser.add_argument("--demo-event", choices=tuple(event.value for event in HostEvent),
                        help="Show a build-time sample message (not actual host dispatch)")
    args = parser.parse_args(argv)
    plugin = creator_workflow(platforms=tuple(args.platforms or PLATFORMS), profile=args.profile)
    path = plugin.build(args.output)
    print(f"Validated PBS Studio v3 plugin: {path}")
    print("Declared permissions:", ", ".join(plugin.manifest()["permissions"]))
    if args.demo_event:
        for item in plugin.manifest().get("notifications", []):
            if item["event"] == args.demo_event:
                print(f"Authoring preview: {item['title']} — {item['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

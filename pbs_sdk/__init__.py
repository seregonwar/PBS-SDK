"""Code-first authoring for PBS Studio's declarative, desktop-only plugin API.

This package runs on the developer's computer. PBS Studio does NOT run Python
or load source files; only the validated JSON manifest crosses into the host.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
import os
from pathlib import Path
import tempfile

from scripts.validate import validate_manifest_document


class HostEvent(str, Enum):
    CONSOLE_CONNECTED = "console.connected"
    CONSOLE_DISCONNECTED = "console.disconnected"
    BROADCAST_STARTED = "broadcast.started"
    BROADCAST_STOPPED = "broadcast.stopped"


class SettingsPage(str, Enum):
    CONSOLES = "open.settings.consoles"
    PLAYBACK = "open.settings.playback"
    STREAMING = "open.settings.streaming"
    APPEARANCE = "open.settings.appearance"


class ManifestError(ValueError):
    """Code-authored manifest failed the exact public host-contract validator."""

    def __init__(self, errors: list[str]):
        self.errors = tuple(errors)
        super().__init__("Plugin manifest rejected:\n- " + "\n- ".join(errors))


@dataclass
class Plugin:
    """Typed builder for *data-only* v3 capabilities.

    Calls to this object only construct declarations. Their Python bodies are
    never shipped or called by PBS Studio. Each feature has its own permission
    inferred from the capabilities requested, with no hidden broad grants.
    """

    id: str
    name: str
    version: str
    description: str
    author: str
    _cards: list[dict[str, str]] = field(default_factory=list, repr=False)
    _actions: list[dict[str, str]] = field(default_factory=list, repr=False)
    _presets: list[dict[str, str]] = field(default_factory=list, repr=False)
    _notifications: list[dict[str, str]] = field(default_factory=list, repr=False)

    def card(self, id: str, *, title: str, description: str,
             button_label: str, url: str) -> Plugin:
        self._cards.append(dict(id=id, title=title, description=description,
                                button_label=button_label, url=url))
        return self

    def shortcut(self, id: str, *, label: str, description: str,
                 target: SettingsPage) -> Plugin:
        self._actions.append(dict(id=id, label=label, description=description,
                                  target=SettingsPage(target).value))
        return self

    def stream_preset(self, id: str, *, name: str, url: str) -> Plugin:
        # Never accept a stream key, password, token or callback parameter.
        self._presets.append(dict(id=id, name=name, url=url))
        return self

    def on(self, event: HostEvent, *, id: str, title: str, message: str) -> Plugin:
        self._notifications.append(dict(id=id, event=HostEvent(event).value,
                                        title=title, message=message))
        return self

    def manifest(self) -> dict:
        permissions: list[str] = []
        if self._cards:
            permissions.extend(("ui.cards", "links.open"))
        if self._actions:
            permissions.append("ui.actions")
        if self._presets:
            permissions.append("stream.presets")
        if self._notifications:
            permissions.append("ui.notifications")
        result: dict = {
            "schema": 3, "api_version": 1, "id": self.id,
            "name": self.name, "version": self.version,
            "description": self.description, "author": self.author,
            "permissions": permissions,
        }
        for key, items in (("cards", self._cards), ("actions", self._actions),
                           ("presets", self._presets), ("notifications", self._notifications)):
            if items:
                # Do not return aliases to the builder's internal lists.
                result[key] = [dict(item) for item in items]
        return result

    def render(self) -> str:
        # Stable ordering/newlines produce reproducible review hashes.
        document = json.dumps(self.manifest(), indent=2, ensure_ascii=False) + "\n"
        errors = validate_manifest_document(document)
        if errors:
            raise ManifestError(errors)
        return document

    def build(self, destination: str | Path) -> Path:
        """Validate before touching output; stage and atomically replace it."""
        document = self.render()
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        staged: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                prefix=f".{path.name}.", suffix=".tmp", delete=False
            ) as output:
                staged = Path(output.name)
                output.write(document)
                output.flush()
                # Atomic replacement suffices for an authoring artifact. Some
                # virtualized Windows volumes stall indefinitely on fsync().
            os.replace(staged, path)
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)
        return path


__all__ = ["Plugin", "HostEvent", "SettingsPage", "ManifestError"]

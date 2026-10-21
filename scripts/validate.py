#!/usr/bin/env python3
"""Validate PBS Studio schema-v1 and schema-v2 declarative plugin manifests.

Requires the development dependency from requirements-dev.txt.
This validator checks JSON Schema plus semantic invariants that a schema alone
cannot express, such as duplicate JSON object keys and duplicate card IDs.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "v1" / "plugin.schema.json"
SCHEMA_PATHS = {
    1: SCHEMA_PATH,
    2: REPO_ROOT / "schemas" / "v2" / "plugin.schema.json",
}
MAX_MANIFEST_BYTES = 64 * 1024
HOST_PATTERN = re.compile(r"[A-Za-z0-9]+(?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9]+(?:[A-Za-z0-9-]*[A-Za-z0-9])?)*\Z")


def _text_errors(value: str, label: str, byte_limit: int) -> list[str]:
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        return [f"{label}: forbidden control character"]
    try:
        byte_count = len(value.encode("utf-8"))
    except UnicodeEncodeError:
        return [f"{label}: invalid Unicode surrogate"]
    if byte_count > byte_limit:
        return [f"{label}: exceeds {byte_limit} UTF-8 bytes"]
    return []


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict:
    output = {}
    for key, value in pairs:
        if key in output:
            raise ValueError(f"duplicate JSON key: {key!r}")
        output[key] = value
    return output


def parse_json_document(document: str) -> object:
    return json.loads(
        document,
        object_pairs_hook=_reject_duplicate_json_keys,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-standard JSON constant: {value}")
        ),
    )


def load_validator(schema_path: Path = SCHEMA_PATH) -> Draft202012Validator:
    schema = parse_json_document(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _valid_host_port(parts: object) -> bool:
    try:
        host = parts.hostname
        port = parts.port
        raw_port = parts.netloc.rsplit(":", 1)[1] if ":" in parts.netloc else None
        return bool(
            host
            and parts.username is None
            and parts.password is None
            and len(parts.netloc) <= 260
            and len(host) <= 253
            and HOST_PATTERN.fullmatch(host)
            and (
                raw_port is None
                or (
                    1 <= len(raw_port) <= 5
                    and raw_port.isascii()
                    and raw_port.isdecimal()
                    and port is not None
                    and port != 0
                )
            )
        )
    except ValueError:
        return False


def _valid_url(url: str, *, scheme: str) -> bool:
    if (
        not url.startswith(f"{scheme}://")
        or "\\" in url
        or any(ord(character) <= 32 or ord(character) >= 127 for character in url)
    ):
        return False
    try:
        parts = urlsplit(url)
        if parts.scheme != scheme or not _valid_host_port(parts):
            return False
        if scheme == "rtmps":
            host = parts.hostname or ""
            suffixes = (".local", ".lan", ".internal", ".localhost", ".home.arpa")
            try:
                ipaddress.ip_address(host)
                return False
            except ValueError:
                pass
            if (
                "." not in host
                or host.lower().endswith(suffixes)
                or host.lower() == "localhost"
                or len(url.encode("utf-8")) > 512
                or len(parts.path) > 96
            ):
                return False
            # A template declares an ingest endpoint for explicit user review.
            # Reject path traversal and URI authority/query/fragment escapes.
            if (
                "?" in url
                or "#" in url
                or host.replace(".", "").isdigit()
                or not re.fullmatch(r"/[A-Za-z0-9_.~/-]{1,95}", parts.path)
                or parts.path.endswith("/")
                or "//" in parts.path
                or any(segment in {".", ".."} for segment in parts.path.split("/"))
            ):
                return False
            host_lower = host.lower()
            if host_lower == "live.twitch.tv" and parts.path != "/app":
                return False
            if host_lower in {"a.rtmps.youtube.com", "b.rtmps.youtube.com"} and parts.path != "/live2":
                return False
        return True
    except ValueError:
        return False


def validate_manifest_document(
    document: str, validator: Draft202012Validator | None = None
) -> list[str]:
    """Return human-readable validation errors, or an empty list on success."""
    try:
        if len(document.encode("utf-8")) > MAX_MANIFEST_BYTES:
            return [f"manifest exceeds {MAX_MANIFEST_BYTES} UTF-8 bytes"]
    except UnicodeEncodeError:
        return ["manifest contains invalid Unicode"]
    try:
        manifest = parse_json_document(document)
    except (ValueError, json.JSONDecodeError) as exc:
        return [f"invalid JSON: {exc}"]

    if not isinstance(manifest, dict):
        return ["manifest must be a JSON object"]

    if validator is None:
        schema_version = manifest.get("schema")
        if type(schema_version) is not int or schema_version not in SCHEMA_PATHS:
            return [f"unsupported manifest schema: {schema_version!r}"]
        validator = load_validator(SCHEMA_PATHS[schema_version])
        if schema_version == 2 and (
            type(manifest.get("api_version")) is not int
            or manifest["api_version"] != 1
        ):
            return ["incompatible API version: v2 requires api_version 1 (major compatibility 1)"]

    schema_errors = sorted(
        validator.iter_errors(manifest),
        key=lambda error: ("/".join(str(part) for part in error.absolute_path), error.message),
    )
    if schema_errors:
        return [
            f"{'/'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
            for error in schema_errors
        ]

    errors: list[str] = []
    for key, max_bytes in (
        ("id", 64),
        ("name", 96),
        ("version", 64),
        ("description", 512),
        ("author", 96),
    ):
        errors.extend(_text_errors(manifest[key], key, max_bytes))
    card_ids: set[str] = set()
    for card in manifest.get("cards", []):
        card_id = card["id"]
        for key, max_bytes in (
            ("id", 64),
            ("title", 96),
            ("description", 512),
            ("url", 2048),
            ("button_label", 48),
        ):
            errors.extend(_text_errors(card[key], f"card {card_id!r}.{key}", max_bytes))
        if card_id in card_ids:
            errors.append(f"duplicate card id: {card_id!r}")
        card_ids.add(card_id)

        url = card["url"]
        if not _valid_url(url, scheme="https"):
            errors.append(f"invalid HTTPS card URL for {card_id!r}")

    if manifest["schema"] == 2:
        action_ids: set[str] = set()
        for action in manifest.get("actions", []):
            action_id = action["id"]
            for key, max_bytes in (
                ("id", 64),
                ("label", 96),
                ("description", 512),
                ("target", 64),
            ):
                errors.extend(_text_errors(action[key], f"action {action_id!r}.{key}", max_bytes))
            if action_id in action_ids:
                errors.append(f"duplicate action id: {action_id!r}")
            action_ids.add(action_id)

        preset_ids: set[str] = set()
        for preset in manifest.get("presets", []):
            preset_id = preset["id"]
            for key, max_bytes in (
                ("id", 64),
                ("name", 96),
                ("url", 512),
            ):
                errors.extend(_text_errors(preset[key], f"stream preset {preset_id!r}.{key}", max_bytes))
            if preset_id in preset_ids:
                errors.append(f"duplicate stream preset id: {preset_id!r}")
            preset_ids.add(preset_id)
            if not _valid_url(preset["url"], scheme="rtmps"):
                errors.append(f"invalid RTMPS ingest template for {preset_id!r}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate declarative PBS Studio v1/v2 plugins")
    parser.add_argument("files", nargs="+", type=Path, help="plugin manifest JSON files")
    args = parser.parse_args(argv)

    failed = False
    for manifest_path in args.files:
        try:
            document = manifest_path.read_text(encoding="utf-8")
            errors = validate_manifest_document(document)
        except (OSError, UnicodeError) as exc:
            errors = [f"failed to read manifest: {exc}"]

        if errors:
            failed = True
            for error in errors:
                print(f"FAIL {manifest_path}: {error}", file=sys.stderr)
        else:
            print(f"PASS {manifest_path}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

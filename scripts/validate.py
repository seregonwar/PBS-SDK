#!/usr/bin/env python3
"""Validate PBS Studio schema-v1 plugin manifests.

Requires the development dependency from requirements-dev.txt.
This validator checks JSON Schema plus semantic invariants that a schema alone
cannot express, such as duplicate JSON object keys and duplicate card IDs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "v1" / "plugin.schema.json"
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

    if validator is None:
        validator = load_validator()

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
    for card in manifest["cards"]:
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
        try:
            parts = urlsplit(url)
            host = parts.hostname
            port = parts.port
            raw_port = parts.netloc.rsplit(":", 1)[1] if ":" in parts.netloc else None
            if (
                parts.scheme != "https"
                or not url.startswith("https://")
                or not host
                or parts.username is not None
                or parts.password is not None
                or len(parts.netloc) > 260
                or len(host) > 253
                or HOST_PATTERN.fullmatch(host) is None
                or (
                    raw_port is not None
                    and (
                        not 1 <= len(raw_port) <= 5
                        or not raw_port.isascii()
                        or not raw_port.isdecimal()
                        or port is None
                        or port == 0
                    )
                )
                or "\\" in url
                or any(ord(character) <= 32 or ord(character) >= 127 for character in url)
            ):
                errors.append(f"invalid HTTPS card URL for {card_id!r}")
        except ValueError:
            errors.append(f"invalid HTTPS card URL for {card_id!r}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate declarative PBS Studio v1 plugins")
    parser.add_argument("files", nargs="+", type=Path, help="plugin manifest JSON files")
    args = parser.parse_args(argv)
    validator = load_validator()

    failed = False
    for manifest_path in args.files:
        try:
            document = manifest_path.read_text(encoding="utf-8")
            errors = validate_manifest_document(document, validator)
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

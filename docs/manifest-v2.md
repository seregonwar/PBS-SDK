# Plugin manifest version 2

PBS Studio plugin manifests remain **declarative JSON**. Schema v2 adds
settings navigation actions and credential-free RTMPS ingest templates.
It does not provide extension code, scripts or access to credentials.
The host supports plugins on Windows, macOS and Linux only; Android and
iOS/iPadOS builds disable plugin support at compile time. The API major and
schema compatibility rules below apply to the desktop host.

See the [working v2 example](../examples/navigation-and-streaming/plugin.json)
and the [versioned v2 JSON Schema](../schemas/v2/plugin.schema.json).

## Compatibility

A v2 plugin uses integer **schema = 2** and integer **api_version = 1**.
The latter declares compatibility with plugin API major version 1. Unknown
major versions are rejected; there is no implicit compatibility fallback.
The plugin's own version remains an independent semantic version.

Existing v1 files, using schema = 1, remain valid as written. PBS Studio
continues to support their cards and HTTPS links; no migration is required.

## Top-level fields

| Key | Required | Description |
| --- | --- | --- |
| schema | Yes | Integer 2 |
| api_version | Yes | Integer 1 (host plugin API major) |
| id | Yes | Stable lowercase letters, digits, dots and hyphens; 1–64 bytes |
| name | Yes | Human-readable name, 1–96 UTF-8 bytes |
| version | Yes | SemVer, such as 1.0.0 or 1.1.0-beta.1 |
| description | Yes | Plain-text summary, up to 512 UTF-8 bytes |
| author | Yes | Attribution, 1–96 UTF-8 bytes |
| permissions | Yes | Unique values from the four capability names |
| cards | No | Up to 16 v1-compatible card objects |
| actions | No | Up to 16 bounded navigation actions |
| presets | No | Up to 8 RTMPS ingest endpoint templates |

Unknown fields are invalid.

## Settings actions

An action has exactly four fields:

| Key | Example |
| --- | --- |
| id | console-settings |
| label | Console settings |
| description | Open console configuration |
| target | open.settings.consoles |

Every action has a unique ID within the actions array. Labels and
descriptions are plain text. Only four **target** strings are allowed:

- open.settings.consoles
- open.settings.playback
- open.settings.streaming
- open.settings.appearance

The plugin must request permission **ui.actions** before exposing actions.
The user must activate a permitted action explicitly. Actions only navigate
to those settings screens; they cannot modify settings or start streaming.
Other app pages, arbitrary URLs, scripts, commands, event hooks, query
parameters and callbacks are invalid.

## RTMPS templates

A preset has exactly these fields:

| Key | Example |
| --- | --- |
| id | generic-rtmps |
| name | Example RTMPS ingest |
| url | rtmps://ingest.example.com/live |

The plugin must request **stream.presets** to offer any stream preset.
The URL identifies an ingest endpoint. It never embeds a stream key, token,
password, account credentials or other secret.

The SDK validator allows only ASCII RTMPS URLs with public dotted DNS-style
hostnames, optional port numbers 1–65535 and a path of at most 96 ASCII
characters from the letters, digits, underscore, hyphen, dot, tilde and slash
set. Paths may include provider application subpaths, such as
/ingest/custom, but cannot be empty, end in a slash, contain empty segments
or use the dot/parent-directory segments. URLs are capped at 512 bytes.
Private/local-use DNS suffixes, IP literal hosts, userinfo, query strings,
fragments, backslashes, non-ASCII URLs and placeholders with braces are
rejected. The official Twitch host is accepted only as the exact URL
rtmps://live.twitch.tv/app, and the canonical YouTube ingest host only as
rtmps://a.rtmps.youtube.com/live2. Alternate port or letter case on those
two known hosts is rejected.

The URL is presented to the user for review before applying it. The format
cannot determine from arbitrary provider path text whether an author placed
a secret in it; authors must supply only public server/application endpoints.
Never put stream keys or authentication tokens in any manifest value.
The user configures any streaming credentials separately in PBS Studio.

A preset is a suggested destination. The host applies it only through a user
action and approved permission. It cannot automatically start a stream,
authenticate or transmit media.

## Permission review and revocation

The four declarative permissions are **ui.cards**, **links.open**,
**ui.actions** and **stream.presets**. A nonempty cards array requires both
ui.cards and links.open; nonempty actions require ui.actions; nonempty
presets require stream.presets.

When installing or updating a plugin, PBS Studio reviews its declared
identity, permissions and changed capabilities with the user. The host
stores permission grants outside the plugin manifest. Files cannot approve
their own capabilities, grant themselves permissions, or override revocation.

Revoking ui.actions disables the plugin's navigation actions; revoking
stream.presets prevents applying those templates. Disabling or removing
the plugin prevents its capabilities from being offered. New permissions
introduced through an update require review before they can be granted.
The host remains responsible for enforcing permission checks at use time.

## Validate v1 and v2

After installing dependencies from requirements-dev.txt, run
**python scripts/validate.py examples/hello-world/plugin.json
examples/navigation-and-streaming/plugin.json** from the repository root,
or run **python -m unittest discover -s tests -p test_*.py -v**.

The CLI selects the schema by version, checks compatibility with API major
1, validates each manifest and exits with a nonzero status if any file is
invalid.

See [host integration and race test guidance](host-integration.md) for
review-to-install integrity checks and concurrent operations.

# Plugin manifest version 3 — in-app event toasts

Schema v3 extends the [v2 declarative manifest](manifest-v2.md), preserving
existing cards, links, navigation actions and RTMPS presets. The plugin
**host API major remains 1**. The new capability is an optional collection of
static in-app notification declarations.

PBS Studio plugins are desktop only: Windows, macOS and Linux. The host build
flag PBS_ENABLE_PLUGINS is ON by default on desktop; Android, iOS and iPadOS
builds disable it and reject attempts to enable it.

See the [v3 JSON Schema](../schemas/v3/plugin.schema.json) and
[event notifications example](../examples/event-notifications/plugin.json).

## Compatibility and fields

Version 3 uses integer schema = 3 and integer api_version = 1. All v2 fields
and limits remain unchanged: metadata, permissions and optional cards
(maximum 16), actions (maximum 16) and presets (maximum 8). It also permits:

| Field | Required | Description |
| --- | --- | --- |
| notifications | No | Up to 8 static in-app toast declarations |

V3 permits up to five distinct permissions: ui.cards, links.open, ui.actions,
stream.presets and **ui.notifications**. The last permission is not valid
in v1 or v2. A nonempty notifications array requires ui.notifications.
Declaring a permission never overrides a host-side revocation.

Existing schema 1 and 2 manifests require no changes. The plugin's own
SemVer version is independent of schema and API version.

## Notification entry

Each notifications item has **exactly** the following fields:

| Field | Type and limit | Example |
| --- | --- | --- |
| id | Lowercase ID, 1–64 ASCII bytes | console-online |
| event | One of four exact names | console.connected |
| title | Nonempty plain text, 1–96 UTF-8 bytes | Console connected |
| message | Nonempty plain text, 1–240 UTF-8 bytes | A console connection has been established. |

IDs must be unique **within the notifications array**. An ID can also
occur in another feature collection: card, action, preset and notification
IDs inhabit independent namespaces. Unknown fields and duplicate JSON
object keys are invalid.

The event allowlist is:

- console.connected
- console.disconnected
- broadcast.started
- broadcast.stopped

PBS Studio shows a **toast inside the application only on an event
transition**; it does not generate notifications at application startup,
plugin reload or restoration of an already-existing connection/broadcast.
Plugins cannot trigger events, receive contextual information or observe
arbitrary event names.

Notification title and message are **static literal text**. The host does
not interpolate variables or placeholders: brace-delimited names,
percent tokens and dollar-prefixed expressions are displayed as ordinary
characters. They do not execute code. The feature has no scripts, native
OS notifications, URL opening, network activity, user data, session context
or credentials.

## Approval, dispatch and revocation

The host reviews the manifest and permissions before installation or update.
Only an enabled plugin with an effective ui.notifications grant can display
its declared toasts on allowed transitions. Revoking the grant or disabling
or removing the plugin denies subsequent event notifications. Host-managed
grants live outside plugin JSON and are preserved across updates.

SDK validation checks manifest shape, uniqueness and text bounds; runtime
event detection and presentation are host responsibilities. It is not a
generic event callback, automation engine or system notification service.

## Validate

From the repository root:

    python -m pip install -r requirements-dev.txt
    python scripts/validate.py examples/hello-world/plugin.json examples/navigation-and-streaming/plugin.json examples/event-notifications/plugin.json
    python -m unittest discover -s tests -p 'test_*.py' -v

See [host integration guidance](host-integration.md) for installation,
permission and filesystem race considerations.

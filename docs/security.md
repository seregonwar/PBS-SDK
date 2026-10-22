# Security model

PBS Studio's plugin manifest formats **v1, v2 and v3 are data only**. They provide
bounded user interface declarations. Plugins cannot execute native code,
scripts, shell commands, arbitrary callbacks, downloaded libraries or
background requests. The host retains control of every capability.

## Declared capabilities

| Permission | Availability | Meaning |
| --- | --- | --- |
| ui.cards | v1, v2 and v3 | Display plain-text plugin cards |
| links.open | v1, v2 and v3 | Open HTTPS links after the user clicks a card |
| ui.actions | v2 and v3 | Navigate to one of four allowlisted settings screens |
| stream.presets | v2 and v3 | Suggest credential-free RTMPS ingest endpoints |
| ui.notifications | v3 only | Show static in-app toast text on four allowed host transitions |

Nonempty cards require ui.cards and links.open together. Nonempty actions
require ui.actions. Nonempty presets require stream.presets. Nonempty
notifications require ui.notifications. Unknown
capabilities are rejected; declaring a permission does not grant it.

## User approval, revocation and updates

The host displays plugin identity and requested permissions for review
during installation. The user controls approval, activation, individual
permission revocation and plugin removal. Permission grants are host state
stored separately from the manifest; a plugin cannot assert that it is
already enabled or approved. Revoked capabilities must not be invoked
even if they remain declared in the file.

When a new manifest changes permissions or declared operations, the host
checks the reviewed data before installation or update. Newly requested
capabilities require their own grant; an update cannot silently bypass a
previous revocation. Disabled or removed plugins are not exposed for
interaction. The host verifies permissions at the moment of use as well.

Manifest versions 2 and 3 require api_version = 1, selecting host API major
compatibility 1. Unsupported major versions are rejected rather than
falling back to an unreviewed execution path. Version 1 manifests are
still supported under their own immutable schema.

## User interface isolation

Manifest strings are untrusted plain text. The application must never
interpret a plugin title, description, action label or preset name as
HTML, script or code. Navigation action targets are restricted to:

- open.settings.consoles
- open.settings.playback
- open.settings.streaming
- open.settings.appearance

Actions are user-initiated navigation only. They cannot change settings,
start capture, start broadcasts, trigger purchases or access account data.
Card links are absolute HTTPS URLs; userinfo, path traversal escapes and
other unsafe URL features should be rejected by the host validator.

## Streaming boundaries

RTMPS presets are untrusted *server destination suggestions*. They contain
only ID, display name and a fixed ingest endpoint URL. The host presents
and applies them after explicit user action and permission approval.
A plugin never receives a stream key, token, password, session credential
or account login. Those values must be managed separately by the host.
Presets never start or stop a stream by themselves.

The SDK validator rejects URL userinfo, query strings, fragments, path
traversal, placeholder braces and non-RTMPS schemes for streaming templates.
Provider-specific application paths are permitted, so the user must review
the ingest endpoint and authors must ensure it contains no secret material.
A URL can still identify an external service that is not endorsed by PBS
Studio. Review destinations before using them.

## Event notification boundaries (schema v3)

The v3 notifications collection contains at most 8 static text rules per
plugin. Only console.connected, console.disconnected, broadcast.started
and broadcast.stopped may trigger a rule. The host presents an in-app toast
only for an actual state transition. It must not dispatch startup/reload
notifications or derive dynamic titles/messages from session data.
The transitions represent aggregate host state (any console connected,
any broadcast live), not per-console or per-session telemetry.
Permission ui.notifications is grant-controlled independently of cards,
links, actions and stream presets. Revocation or disablement denies display.

These declarations cannot access native/system notification APIs, process
or network data, stream keys, arbitrary callbacks, URLs or event payloads.
Notification text is literal and untrusted. Dollar characters, braces or
percent tokens are never interpolated, evaluated or treated as formatting
commands. The host can limit the number of toasts displayed per transition
regardless of how many plugins are installed.

## Structural validation

The SDK uses JSON Schema draft 2020-12 plus semantic checks to reject
unknown properties, malformed or duplicate JSON keys, duplicate IDs,
unsafe URLs, oversized files, control characters and incompatible API
versions. PBS Studio must enforce its own checks independently because
an untrusted author need not run the SDK validator.

The manifest size limit is 64 KiB. Plain-text field limits are checked in
UTF-8 bytes, and identifiers are constrained to lowercase ASCII letters,
digits, dots and hyphens. The SDK's complete regression suite includes
adversarial URL, permission and API-version cases.

New capabilities that would require code execution or privileged resources
need separate designs and independently demonstrable isolation. The v1/v2/v3
manifest format does not provide them.

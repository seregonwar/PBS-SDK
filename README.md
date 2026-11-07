# PBS SDK

The public **PBS Studio** declarative plugin SDK. This repository contains
versioned JSON schemas, a **code-first Python authoring toolkit**, working
examples, documentation, a validator, and adversarial compatibility tests.

**Availability:** PBS Studio accepts plugins on **desktop only** (Windows,
macOS and Linux). Android, iOS and iPadOS builds deliberately exclude the
plugin manager and its UI. The host's `PBS_ENABLE_PLUGINS` build flag defaults
to ON on desktop and OFF on mobile; mobile configurations reject enabling it.
This platform restriction does not change the v1/v2 manifest schemas or API.

**Current format: v5 (API major 2)**, with continued support for v1–v4.
V5 adds the first executable format, modelled on MemDBG's script plugins: a
plugin embeds Lua in its reviewed manifest and the host runs it in a sandbox
with only the approved host APIs. See the
[v5 specification](docs/manifest-v5.md),
[Lua host API reference](docs/lua-api.md) and
[script panel example](examples/script-panel/plugin.json).
V4 remains current for declarative plugins and adds a dedicated tools workspace
with live stream and GPU diagnostic panels. Declarative plugins can display
cards, open HTTPS links, navigate to approved settings screens, offer
credential-free RTMPS ingest templates and declare static in-app event toasts.
The SDK still never ships or loads native libraries, scripts from disk or
downloaded code: v5 source travels inside the hashed manifest.

## Create a plugin

### Create a plugin in Python

The [Creator Workflow Companion](examples/creator-workflow/README.md) is a
tested code-first source project. Python selects Twitch/YouTube workflow
profiles, builds RTMPS templates, adds operator cards and settings shortcuts,
and declares notifications for console/broadcast transitions.

```sh
python -m pip install -r requirements-dev.txt
python examples/creator-workflow/build.py --profile production
python scripts/validate.py examples/creator-workflow/dist/plugin.json
```

Your own project can use `from pbs_sdk import Plugin, HostEvent, SettingsPage`.
See the [authoring guide](docs/python-authoring.md). **Python runs only on
the developer's computer at build time**; PBS Studio imports the validated
JSON output but does not run scripts or native code.

### Author a manifest directly

1. Start with the [script panel example](examples/script-panel/plugin.json)
   (executable, schema 5), the [v3 event notifications example](examples/event-notifications/plugin.json),
   the [v2 navigation and streaming example](examples/navigation-and-streaming/plugin.json)
   or the [v1 card example](examples/hello-world/plugin.json).
2. Give your plugin a stable lowercase ID and update its metadata. A script
   plugin needs schema = 5, api_version = 2, a `runtime` block and the
   `runtime.script` permission.
3. Validate the JSON and import it into PBS Studio. Review and approve the
   requested permissions before enabling capabilities. Script plugins show an
   extra warning because their code runs inside PBS Studio.

From the repository root:

    python -m pip install -r requirements-dev.txt
    python scripts/validate.py examples/script-panel/plugin.json examples/stream-inspector/plugin.json examples/hello-world/plugin.json examples/navigation-and-streaming/plugin.json examples/event-notifications/plugin.json

The permissions **ui.cards** and **links.open** allow interactive cards.
Version 2 adds **ui.actions** for bounded settings navigation and
**stream.presets** for RTMPS ingest templates. PBS Studio controls grants,
revocation and whether each plugin is enabled. Version 3 adds
**ui.notifications** for static in-app event toasts. Version 5 adds
**runtime.script** plus the host APIs **api.host**, **api.store**, **api.ui**
and **api.file**; the sandbox has no file system, process, network or native
module access.

## Specifications

- [V5 script runtime specification](docs/manifest-v5.md)
- [V5 Lua host API reference](docs/lua-api.md)
- [V5 versioned JSON schema](schemas/v5/plugin.schema.json)
- [V5 script panel example](examples/script-panel/plugin.json)
- [V4 tools workspace specification](docs/manifest-v4.md)
- [V3 event notification specification](docs/manifest-v3.md)
- [V3 versioned JSON schema](schemas/v3/plugin.schema.json)
- [V3 event notifications example](examples/event-notifications/plugin.json)
- [V2 manifest and API compatibility](docs/manifest-v2.md)
- [V2 versioned JSON schema](schemas/v2/plugin.schema.json)
- [V2 navigation and RTMPS example](examples/navigation-and-streaming/plugin.json)
- [V1 manifest reference](docs/manifest-v1.md)
- [V1 versioned JSON schema](schemas/v1/plugin.schema.json)
- [V1 card example](examples/hello-world/plugin.json)
- [Permissions and security model](docs/security.md)
- [Host integration and filesystem race test guidance](docs/host-integration.md)

Manifest schema versions are distinct from a plugin's semantic version.
V2 and v3 require host API major 1; legacy v1 and v2 remain valid unchanged.

## Validation and contributions

Tests require Python 3.10+:

    python -m pip install -r requirements-dev.txt
    python -m unittest discover -s tests -p 'test_*.py' -v

GitHub Actions validates the three declarative examples, compiles the Python
creator example, and runs adversarial, permission and compatibility tests.
No private PBS Studio implementation or account secrets are
distributed by this repository.

Released under the [MIT License](LICENSE).

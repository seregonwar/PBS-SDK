# PBS SDK

The public **PBS Studio** declarative plugin SDK. This repository contains
versioned JSON schemas, a **code-first Python authoring toolkit**, working
examples, documentation, a validator, and adversarial compatibility tests.

**Availability:** PBS Studio accepts plugins on **desktop only** (Windows,
macOS and Linux). Android, iOS and iPadOS builds deliberately exclude the
plugin manager and its UI. The host's `PBS_ENABLE_PLUGINS` build flag defaults
to ON on desktop and OFF on mobile; mobile configurations reject enabling it.
This platform restriction does not change the v1/v2 manifest schemas or API.

**Current format: v4 (API major 1)**, with continued support for v1, v2 and v3.
V4 adds a dedicated tools workspace with live stream and GPU diagnostic panels,
available from Home and the stream overlay. See the
[v4 specification](docs/manifest-v4.md) and
[Stream Inspector example](examples/stream-inspector/plugin.json).
Plugins can display cards, open HTTPS links, navigate to approved settings
screens, offer credential-free RTMPS ingest templates and declare static
in-app event toasts. The SDK does not execute scripts, native libraries or
downloaded code.

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

1. Start with the [v3 event notifications example](examples/event-notifications/plugin.json),
   [v2 navigation and streaming example](examples/navigation-and-streaming/plugin.json)
   or [v1 card example](examples/hello-world/plugin.json).
2. Give your plugin a stable lowercase ID and update its metadata. For v3,
   set schema = 3 and api_version = 1.
3. Validate the JSON and import it into PBS Studio. Review and approve the
   requested permissions before enabling capabilities.

From the repository root:

    python -m pip install -r requirements-dev.txt
    python scripts/validate.py examples/hello-world/plugin.json examples/navigation-and-streaming/plugin.json examples/event-notifications/plugin.json

The permissions **ui.cards** and **links.open** allow interactive cards.
Version 2 adds **ui.actions** for bounded settings navigation and
**stream.presets** for RTMPS ingest templates. PBS Studio controls grants,
revocation and whether each plugin is enabled. Version 3 adds
**ui.notifications** for static in-app event toasts (no startup toasts,
native notifications, or scripts).

## Specifications

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

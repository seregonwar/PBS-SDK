# PBS SDK

The public **PBS Studio** declarative plugin SDK. This repository contains
versioned JSON schemas, working examples, documentation, a validator, and
adversarial compatibility tests.

**Availability:** PBS Studio accepts plugins on **desktop only** (Windows,
macOS and Linux). Android, iOS and iPadOS builds deliberately exclude the
plugin manager and its UI. The host's `PBS_ENABLE_PLUGINS` build flag defaults
to ON on desktop and OFF on mobile; mobile configurations reject enabling it.
This platform restriction does not change the v1/v2 manifest schemas or API.

**Current format: v2 (API major 1)**, with continued support for legacy v1.
Plugins can display cards, open HTTPS links, navigate to approved settings
screens and offer credential-free RTMPS ingest server templates. The SDK does
not execute scripts, native libraries or downloaded code.

## Create a plugin

1. Start with the [v2 navigation and streaming example](examples/navigation-and-streaming/plugin.json)
   or the [v1 card example](examples/hello-world/plugin.json).
2. Give your plugin a stable lowercase ID and update its metadata. For v2,
   set schema = 2 and api_version = 1.
3. Validate the JSON and import it into PBS Studio. Review and approve the
   requested permissions before enabling capabilities.

From the repository root:

    python -m pip install -r requirements-dev.txt
    python scripts/validate.py examples/hello-world/plugin.json examples/navigation-and-streaming/plugin.json

The permissions **ui.cards** and **links.open** allow interactive cards.
Version 2 adds **ui.actions** for bounded settings navigation and
**stream.presets** for RTMPS ingest templates. PBS Studio controls grants,
revocation and whether each plugin is enabled.

## Specifications

- [V2 manifest and API compatibility](docs/manifest-v2.md)
- [V2 versioned JSON schema](schemas/v2/plugin.schema.json)
- [V2 navigation and RTMPS example](examples/navigation-and-streaming/plugin.json)
- [V1 manifest reference](docs/manifest-v1.md)
- [V1 versioned JSON schema](schemas/v1/plugin.schema.json)
- [V1 card example](examples/hello-world/plugin.json)
- [Permissions and security model](docs/security.md)
- [Host integration and filesystem race test guidance](docs/host-integration.md)

Manifest schema versions are distinct from the version of a plugin. V2
explicitly requires API major compatibility 1, and v1 files remain valid
without modification.

## Validation and contributions

Tests require Python 3.10+:

    python -m pip install -r requirements-dev.txt
    python -m unittest discover -s tests -p 'test_*.py' -v

GitHub Actions validates both published examples and runs adversarial,
permission, schema compatibility and unsupported API-version tests on each
pull request. No private PBS Studio implementation or account secrets are
distributed by this repository.

Released under the [MIT License](LICENSE).

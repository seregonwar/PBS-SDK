# PBS SDK

The public plugin manifest specification for **PBS Studio**. This repository
contains a versioned JSON Schema, a complete example, documentation, and tests
for creating third-party plugins.

**Current format: v1 — declarative JSON only.** Plugins can display cards and
offer links to HTTPS websites. The format does not execute plugins, scripts,
native libraries, or downloaded code.

## Start with a plugin

1. Copy [\`examples/hello-world/plugin.json\`](examples/hello-world/plugin.json).
2. Give your plugin a unique lowercase \`id\`, update its metadata and cards,
   and keep \`schema\` at \`1\`.
3. Run the validator, then import the manifest into the PBS Studio plugin
   manager when support is available in your installed build.

\`\`\`bash
python -m pip install -r requirements-dev.txt
python scripts/validate.py examples/hello-world/plugin.json
\`\`\`

The manifest must request \`ui.cards\` and \`links.open\` to declare
interactive cards, and each card's \`url\` must use HTTPS.

## Specification

- [Manifest v1 field reference](docs/manifest-v1.md)
- [Versioned JSON Schema](schemas/v1/plugin.schema.json)
- [Security model and permissions](docs/security.md)
- [Working example](examples/hello-world/plugin.json)

Schema version \`1\` is separate from the plugin's own semantic \`version\`.
The v1 schema path is stable; breaking format changes will use \`v2\` rather
than changing the meaning of v1.

## Verify and contribute

Run tests locally with Python 3.10+:

\`\`\`bash
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -p 'test_*.py' -v
\`\`\`

GitHub Actions performs schema validation, checks the example, and runs a
dedicated suite of valid and adversarial manifests on every pull request.
See [LICENSE](LICENSE) for the MIT license.

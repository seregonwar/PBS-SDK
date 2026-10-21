# Plugin manifest version 1

A plugin is one UTF-8 JSON file. All listed fields are required.

| Field | Type | Meaning |
| --- | --- | --- |
| \`schema\` | integer \`1\` | Manifest format version |
| \`id\` | string | Stable, lowercase dotted or hyphenated identifier |
| \`name\` | string | Human-readable plugin name |
| \`version\` | string | SemVer \`MAJOR.MINOR.PATCH\`, with optional prerelease/build suffix |
| \`description\` | string | Plain-text plugin summary |
| \`author\` | string | Displayed attribution |
| \`permissions\` | string array | Subset of \`ui.cards\` and \`links.open\`, without repeats |
| \`cards\` | array | Zero or more declarative cards |

Every card has these five required fields:

| Field | Type | Meaning |
| --- | --- | --- |
| \`id\` | string | Unique identifier within this plugin |
| \`title\` | string | Plain-text heading |
| \`description\` | string | Plain-text body |
| \`url\` | string | Absolute HTTPS link without URL credentials |
| \`button_label\` | string | Text on the link button |

If \`cards\` contains items, the plugin must declare **both** \`ui.cards\`
and \`links.open\`. Other permissions and extension fields are not supported.
The host's stored enabled/disabled state is separate from this file; do not add
an \`enabled\` field to the manifest.

Manager limits: the manifest is at most 64 KiB of UTF-8 JSON and contains at
most 16 cards. Plugin and card IDs are 1–64 ASCII characters, using lowercase
letters, digits, dots, and hyphens without adjacent or edge separators. Names
are at most 96 UTF-8 bytes; plugin descriptions at most 512; authors at most
96. Card titles are at most 96 bytes, descriptions at most 512, and button
labels at most 48. HTTPS URLs are at most 2048 ASCII bytes, use a DNS-style
hostname (no embedded credentials or IPv6 syntax), and may specify a TCP port.

This reference is implemented by
[\`schemas/v1/plugin.schema.json\`](../schemas/v1/plugin.schema.json).
See [the example](../examples/hello-world/plugin.json) for a working manifest,
and [the security model](security.md) for the trust boundaries.

## Compatibility and upgrades

The integer \`schema\` selects the manifest format. Version 1 consumers
should reject unsupported values, invalid JSON, and unknown fields. The plugin
\`id\` remains stable through upgrades; \`version\` changes when plugin
content changes. A future incompatible schema requires a new manifest schema
number and its own versioned specification.

SDK validation:

\`\`\`console
python -m pip install -r requirements-dev.txt
python scripts/validate.py examples/hello-world/plugin.json
python -m unittest discover -s tests -v
\`\`\`

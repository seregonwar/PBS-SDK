# Security model

PBS Studio plugin manifests in schema version 1 are **data only**. They can
declare cards in the application interface and HTTPS URLs that open when a
person clicks a card's button.

Version 1 has exactly two permissions:

- \`ui.cards\`: display the plugin's cards.
- \`links.open\`: open a card's HTTPS destination on an explicit user action.

There are no script hooks, process execution, dynamic library loading, plugins
that run native code, background networking, access to streaming sessions,
credentials, files, shell commands, or arbitrary application APIs. Those
capabilities are intentionally absent from the v1 format.

The host must treat all manifest strings as untrusted text. In particular,
descriptions and titles are plain text, never HTML or markup. URLs must be
validated before storage and again before opening, be absolute HTTPS URLs,
and contain no embedded user credentials. The user controls plugin
installation, enabled state, and removal in the host application.

The JSON Schema rejects unknown fields, unexpected permission names, and
unsupported schema versions. The SDK validator adds checks for duplicate JSON
keys, duplicate card IDs, and malformed or credential-bearing HTTPS links.
Applications consuming the format should enforce those checks independently
and must not infer that an untrusted plugin author is endorsed by PBS Studio.

A manifest may link to an external website. Opening that site leaves PBS
Studio's trust boundary; apply the same caution as with any ordinary web link.
The HTTPS restriction protects URL schemes but does not endorse external sites
or establish that their content is safe.

The schema major version is immutable: breaking changes require a new
\`schemas/vN/\` directory and manifest \`schema\` value. A plugin's
\`version\` describes the plugin and does not change schema compatibility.

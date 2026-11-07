# Manifest schema v5: embedded script plugins

Schema v5 is the first executable PBS Studio plugin format. A plugin carries a
Lua program inside its own reviewed manifest; the host runs it in a sandbox and
draws the panels the program builds. It is modelled on the script plugins used
by MemDBG: plugin code plus host-provided APIs, not a plugin-specific UI toolkit
and not a native library.

Schema v5 requires `api_version: 2` (the script runtime API major). Schemas
v1–v4 keep their existing `api_version: 1` contract and remain valid.

## Manifest

```json
{
  "schema": 5,
  "api_version": 2,
  "id": "com.example.dlss5",
  "name": "DLSS 5 runtime manager",
  "version": "0.1.0",
  "description": "Checks the DLSS 5 NGX package and stores upscaling preferences.",
  "author": "Example Author",
  "permissions": ["runtime.script", "api.host", "api.store", "api.ui", "api.file"],
  "runtime": {
    "language": "lua",
    "api": 2,
    "source": "pbs.ui.panel(\"main\", \"Runtime\", function()\n  pbs.ui.text(\"Hello\")\nend)"
  }
}
```

The declarative v1–v4 fields (`cards`, `actions`, `presets`, `notifications`,
`panels`) are still allowed and need their usual permissions. A v5 manifest must
also declare `runtime`.

### `runtime`

| Field | Required | Meaning |
| --- | --- | --- |
| `language` | yes | `"lua"` is the only supported value. |
| `source` | yes | UTF-8 Lua source, 1 byte to 48 KiB, without NUL or control characters other than tab, newline and carriage return. |
| `api` | no | When present it must be `2`. |

There is deliberately no entry path, file name, URL or binary reference. The
source is part of the document that is reviewed, SHA-256 hashed, installed and
re-read; tampering with the stored manifest invalidates the plugin.

## Permissions

| Permission | Grants |
| --- | --- |
| `runtime.script` | Execute the embedded source. Required whenever `runtime` is present. |
| `api.host` | Read the host version and the closed metric list, and open approved settings pages. |
| `api.store` | Persist up to 8 KiB (64 keys) of the plugin's own typed settings. |
| `api.ui` | Build the plugin's own panel and show short bounded in-app messages. |
| `api.file` | Probe one absolute file path: existence, regular-file status, size and optional SHA-256. |

Every permission is a maximum request. The host stores grants separately, shows
them individually, and re-checks them on every call. Revoking or disabling the
plugin stops the VM, and an ungranted call raises a Lua error instead of
returning data.

## Runtime limits

| Limit | Value |
| --- | --- |
| Instructions per call | 2,000,000 Lua VM instructions |
| VM memory | 8 MiB |
| Panels per plugin | 4 |
| Widgets per panel frame | 96 |
| Retained log lines | 200 × 300 characters |
| Stored settings | 8 KiB, 64 keys, keys ≤ 64 bytes, strings ≤ 2048 bytes |
| File probe path | absolute, ≤ 512 bytes, hash limited to 512 MiB |

The sandbox opens `base`, `string`, `table`, `math`, `utf8` and `coroutine`.
`io`, `os`, `package`, `require`, `dofile`, `loadfile`, `load`, `loadstring`,
`debug` and `collectgarbage` are removed from the globals. `print` is routed to
the plugin's own log.

## Security position

Script plugins widen the trust boundary relative to v1–v4: a granted
`runtime.script` program runs in-process with the host APIs above. The sandbox
prevents file, process, network, package and native-module access and the host
re-checks grants at each call, but it is not an operating-system sandbox against
a memory-safety defect in the interpreter or in PBS Studio itself. Install
script plugins only from authors you trust.

Native plugin binaries remain unsupported. A v5 plugin can *inspect* a file the
user points at (for example a vendor DLL) but PBS Studio never loads or executes
it.

## Compatibility

- A v5 host rejects a v5 manifest with any `api_version` other than `2`.
- A v4 host rejects schema 5 as unsupported; plugins targeting older hosts
  should keep publishing v4 manifests.
- v1–v4 manifests remain valid on v5 hosts, unchanged.

See the [Lua host API reference](lua-api.md) for every call and widget.

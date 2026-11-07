# Lua host API reference (schema v5, API major 2)

A schema v5 plugin's `runtime.source` runs once at load time and may register up
to four panels. Each panel builder runs once per frame while its panel is
visible. All calls below are checked against the plugin's current grants.

## Globals

| Name | Type | Meaning |
| --- | --- | --- |
| `pbs` | table | The host API (this document). |
| `pbs.api_version` | integer | `2`. |
| `pbs.plugin` | table | `{ id, name, version }` of the running plugin. |
| `pbs.host` | table | `{ name = "PBS Studio", version, os, api = 2 }`. |
| `print(...)` | function | Writes one line to the plugin log. |

Base Lua libraries: `string`, `table`, `math`, `utf8`, `coroutine` and the base
functions. `io`, `os`, `package`, `require`, `dofile`, `loadfile`, `load`,
`loadstring`, `debug` and `collectgarbage` are not available.

## Host services

```lua
pbs.log(level, text)          -- level: "info" | "warn" | "error"
pbs.metric(name)              -- number | string | boolean | nil, permission api.host
pbs.navigate(target)          -- boolean, permission api.host
pbs.notify(title, message)    -- boolean, permission api.ui, one per second
```

`pbs.metric` accepts only the closed list below. Unknown names return `nil`.

| Metric | Type |
| --- | --- |
| `console.connected` | boolean |
| `stream.frames` | number |
| `stream.resolution` | string (`"1920 x 1080"`) |
| `stream.decoder` | string |
| `stream.color` | string |
| `stream.enhancement_ms` | number |
| `broadcast.active` | boolean |
| `broadcast.frames` | number |
| `broadcast.dropped` | number |
| `graphics.device` | string |

`pbs.navigate` accepts the same closed targets as v2 actions:
`open.settings.consoles`, `open.settings.playback`, `open.settings.streaming`,
`open.settings.appearance`.

## Storage

```lua
pbs.store.set(key, value)     -- string | whole number | boolean | nil to delete
pbs.store.get(key)            -- value or nil
```

Permission `api.store`. At most 64 keys, 8 KiB serialized, keys ≤ 64 bytes,
strings ≤ 2048 bytes. The file is written atomically after each change and
survives restarts and updates.

## File probe

```lua
local info = pbs.file.probe("C:\\tools\\nvngx_dlssnr.dll", true)
-- info = { exists, regular, size, sha256? }
```

Permission `api.file`. The path must be absolute, at most 512 bytes, and must
not be a symlink or non-regular file. Directories are never listed. `sha256` is
returned only when requested and the file is at most 512 MiB.

## Panels

```lua
pbs.ui.panel(id, title, build_function, description)
```

`id` is lowercase with dots or hyphens, `title` ≤ 96 bytes, optional
`description` ≤ 512 bytes. Register at most four panels, once, at load time.

Inside `build_function`:

| Call | Returns | Notes |
| --- | --- | --- |
| `pbs.ui.text(text)` | – | Paragraph. |
| `pbs.ui.note(text)` | – | Muted paragraph. |
| `pbs.ui.separator()` | – | Horizontal rule. |
| `pbs.ui.badge(text, level)` | – | `level`: `info`, `good`, `warn`, `danger`. |
| `pbs.ui.metric(name, label)` | – | Host-rendered metric row (`api.host` also required). |
| `pbs.ui.button(id, label)` | boolean | True once, on the frame after a click. |
| `pbs.ui.checkbox(id, label, default)` | boolean | Stored for the life of the VM. |
| `pbs.ui.slider(id, label, min, max, step, default)` | number | Clamped. |
| `pbs.ui.input(id, label, default)` | string | Plain text field. |
| `pbs.ui.combo(id, label, items, default_index)` | number | Zero-based index. |
| `pbs.ui.table(headers, rows)` | – | Up to 8 columns and 32 rows. |

Widget ids are scoped to the plugin. A panel frame may emit at most 96 widgets;
exceeding that fails the frame with a diagnostic shown in the panel.

Clicks are delivered once: a click during frame N is visible to
`pbs.ui.button` during frame N+1, and not again afterwards. Because builders
are immediate-mode, a value you change in response to a click is visible in the
following frame.

## Example

```lua
local function state(key, fallback)
  local value = pbs.store.get(key)
  if value == nil then return fallback end
  return value
end

pbs.ui.panel("main", "My tool", function()
  pbs.ui.metric("stream.resolution", "Stream")
  local path = pbs.ui.input("path", "File to check", state("path", ""))
  pbs.store.set("path", path)
  if pbs.ui.button("check", "Check file") then
    local info = pbs.file.probe(path, true)
    pbs.notify("Check", info.exists and "File found" or "File not found")
  end
end, "A short description shown under the title")
```

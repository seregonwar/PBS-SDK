# Tools workspace (manifest v4, host API 1)

Plugins open from **Home → Plugins** and the stream overlay's **Plugins**
button. They have a dedicated workspace, separate from Settings. Versions 1,
2 and 3 remain supported unchanged.

V4 adds host-rendered diagnostic panels, inspired by the organized tools and
capability model of debugging applications such as MemDBG. This is a PBS
implementation for stream and graphics diagnostics, not a MemDBG binary or
protocol integration. It does not inspect console process memory or execute
Lua, Python or native modules. Those would require a separate runtime and a
console-side debugging transport.

Declare `tools.panels` and up to four `panels`. Each requires `id`, `title`,
`description` and a nonempty `metrics` list. IDs must be unique within panels;
each panel can select up to ten unique metrics. Titles and descriptions use
the same UTF-8 byte limits as cards (96 and 512 bytes).

| Metric | Value |
| --- | --- |
| `console.connected` | Selected console connection state |
| `stream.frames` | Decoded frame count |
| `stream.resolution` | Received picture dimensions |
| `stream.decoder` | Active hardware/software backend |
| `stream.color` | Active colour conversion path |
| `stream.enhancement_ms` | Enhancement GPU time in milliseconds |
| `broadcast.active` | Broadcast live/stopped state |
| `broadcast.frames` | Submitted broadcast frames |
| `broadcast.dropped` | Dropped broadcast frames |
| `graphics.device` | Renderer graphics device name |

The host renders its existing snapshot only while the workspace is visible.
Panels create no workers, timers, subscriptions, history buffers or network
requests. Missing stream values show an unavailable state. Revoking
`tools.panels` or disabling the plugin removes its panels immediately.
Account credentials, addresses, tokens and frame pixels are never exposed.

```python
from pbs_sdk import Plugin, Metric

plugin = Plugin("dev.example.inspector", "Inspector", "1.0.0",
                "Stream health at a glance", "Example")
plugin.panel("stream", title="Stream health", description="Selected console",
             metrics=[Metric.STREAM_DECODER, Metric.STREAM_RESOLUTION,
                      Metric.ENHANCEMENT_MS])
plugin.build("dist/plugin.json")
```

The builder emits v4 when panels are present and retains v3 otherwise. See
[Stream Inspector](../examples/stream-inspector/plugin.json) and the
[v4 JSON schema](../schemas/v4/plugin.schema.json).

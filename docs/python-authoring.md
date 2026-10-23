# Python code-first authoring

PBS Studio supports writing **developer-side Python source** to build schema
v3 manifests. Developers can organize a project into modules, test their
configuration, conditionally assemble capabilities and generate deterministic
installation files. The host accepts only the generated declarative JSON.

**Python never runs inside PBS Studio.** This does not add scripting hooks,
native code, OS notifications, access to session data, callbacks or stream
keys. Runtime-programmable third-party code needs a separate, verified sandbox
and is intentionally unsupported.

## Run the serious source example

Clone PBS-SDK and run from the repository root (Python 3.10+):

```sh
python -m pip install -r requirements-dev.txt
python examples/creator-workflow/build.py --profile production \
  --platform twitch --platform youtube
python scripts/validate.py examples/creator-workflow/dist/plugin.json
python -m unittest discover -s tests -p 'test_*.py'
```

[`examples/creator-workflow/build.py`](../examples/creator-workflow/build.py)
implements a creator's streaming runbook with two clickable HTTPS guides,
two internal settings shortcuts, developer-selectable Twitch/YouTube RTMPS
endpoints, and event-driven broadcast reminders. For a lighter profile:

```sh
python examples/creator-workflow/build.py --profile quick \
  --platform twitch --output examples/creator-workflow/dist/quick.json
```

## Use the typed SDK

```python
from pbs_sdk import Plugin, HostEvent, SettingsPage

plugin = Plugin(
    id="dev.example.workflow", name="Workflow", version="1.0.0",
    description="Broadcast setup companion", author="Example Developer",
)

plugin.shortcut(
    "open-streaming", label="Go to streaming",
    description="Check destinations", target=SettingsPage.STREAMING,
)
plugin.stream_preset("twitch", name="Twitch", url="rtmps://live.twitch.tv/app")
plugin.on(HostEvent.BROADCAST_STARTED, id="check-live",
          title="Stream started", message="Review audio sync and privacy.")
plugin.build("dist/plugin.json")
```

Other available methods are `.card()` and `.render()`. Permissions are
inferred only from requested features and are always reviewed and revocable
in PBS Studio. `build()` invokes the same public validator as the CLI, rejects
bad manifests before modifying the output, and stages/atomically replaces a
deterministic UTF-8 JSON file.

## Testing against the native host

The public unit tests check the real Python source, optional profiles,
permission inference, valid output, rejection of unsafe URLs and duplicates,
and a CLI roundtrip. The private PBS Studio development tree also includes a
`pbs_plugin_developer_smoke` executable that accepts the compiled JSON and
exercises the actual C++ manager's review, installation, persistence, event
dispatch, revocation, disable and uninstall paths.

On a desktop build with plugins enabled, open **Home > Plugins > Review
manifest**, select the generated `dist/plugin.json`, review the permissions
and approve installation. Changing source alone does not modify an installed
plugin; rebuild and explicitly approve a versioned update. Desktop only;
mobile builds do not ship the plugin host.

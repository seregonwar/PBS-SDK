# Creator Workflow — broadcast operator runbook

This is practical production guidance linked from the Creator Workflow
Companion plugin. Its manifest provides the link; it never reads a stream key,
connects to a streaming service or starts a broadcast on your behalf.

## Before connecting

1. Verify your console is reachable on the local network and that the chosen
   source shows the correct picture and sound.
2. Select the expected resolution and frame rate. Compare the video format,
   decoder, playback buffering and visual enhancements with the intended use.
3. Avoid displaying personal account details or other sensitive information
   in any area that could become part of the captured game picture.

## Before broadcasting

1. In **PBS Studio > Streaming**, choose an ingest provider. A plugin stream
   preset sets the RTMPS **server address only**, never a stream key.
2. Obtain a current stream key from your own provider account, enter it in
   PBS Studio's protected destination editor and save it yourself.
3. Set destination names clearly if simulcasting; check each service's
   current requirements, terms and account permissions before going live.
4. Review audio sync, picture sharpness, internet upload headroom and any
   overlays. Confirm the live destination is the account you expect.
5. Start the broadcast manually. The plugin cannot push this button.

## While live

1. Watch the service dashboards independently: PBS Studio's host events
   report that a broadcast became live, **not** that the public service is
   successfully reaching every viewer.
2. Check dropped frames, network retries and audio synchronization. A plugin
   notification is a reminder, not a health measurement or reliability SLA.
3. If the last console disconnects, review capture/source status before
   resuming. Reconnect rather than assuming the plugin can recover it.

## After the broadcast

1. Stop each live destination from PBS Studio.
2. Check recordings, markers and dashboard warnings; avoid keeping secrets
   in screenshots or publicly shared logs.
3. If a stream key was exposed, revoke/rotate it in the provider dashboard.

## Operational limitations

This SDK example has no host observability into bitrate, per-console events,
audio quality, stream keys, account tokens or personal data. Plugin events
are aggregate transitions only: none-connected → at-least-one-connected,
and none-live → live, plus the reverse. PBS Studio displays text-only
notifications inside the application and applies cooldowns and permission
checks. Python runs solely when the developer builds this manifest.

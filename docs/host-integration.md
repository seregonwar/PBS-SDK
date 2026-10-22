# Host integration and adversarial operation checks

This page is a checklist for third-party implementations of the public PBS
Studio declarative plugin protocol. It describes desired observable security
properties, not an attestation of any specific host implementation.

## Review, installation and updates

Treat both manifest versions as untrusted data. Read no more than 64 KiB
from a regular UTF-8 JSON file, validate its exact schema and present its
permissions and intended operations for explicit user approval. The
manifest cannot supply an executable entrypoint, script or generic API call.

1. Preview exact source bytes and their SHA-256 digest. Open the import file
   safely again at installation and reject a digest mismatch.
2. Derive the installed filename from the validated plugin ID under a
   controlled plugin directory. Ignore source-supplied filenames and paths.
3. For updates, review changed destinations/actions. Newly requested
   permissions require approval, and previously revoked grants remain
   revoked after updates.
4. Persist state with bounded, atomic staged writes in the destination
   directory. Handle partial writes and disk errors without treating
   corrupted state as an authorization grant.
5. Before dispatching a card, action or preset, confirm its manifest and
   current enabled state and per-permission grant. Fail closed if missing,
   modified, invalid, revoked or removed.

## Filesystem races, concurrency and parent swaps

Checking a pathname once does not guarantee that a later read, rename or
delete refers to the same object. A concurrently replaced ancestor,
symlink, junction or reparse point may redirect operations. Hosts should
prefer operating on verified, pinned filesystem handles:

| System | Recommended operation |
| --- | --- |
| Linux/POSIX | Traverse directories with openat and O_DIRECTORY, O_NOFOLLOW and O_CLOEXEC, hold parent descriptors, and use handle-relative reads, writes, renameat/linkat/unlinkat. Verify the file identity and regular-file/link-count invariants. |
| Windows | Pin and verify parent directory handles, reject reparse points and junctions, use verified relative handles for operations where supported, and compare identities before relying on file contents. |
| Both | Serialize writers across processes with a safely anchored lock, or reject stale snapshots using optimistic versions. Never overwrite a newer revocation or permission-state change. |

Pin **source** and managed **destination** parents independently. A safe
leaf-open cannot compensate for an untrusted parent path. If a platform
cannot implement race-resistant relative writes, document that limitation
and avoid claiming that a pathname check removes the risk.

## Adversarial integration scenarios

Use isolated temporary directories and independent processes. Barriers
around the open/save/remove points make races easier to reproduce than
arbitrary sleeps.

| Test | Required result |
| --- | --- |
| Replace reviewed source before import | Digest mismatch; changed contents are not installed |
| Swap source parent for a symlink or reparse point | Reject unsafe path or remain anchored to the previously verified directory |
| Swap managed plugin parent before save or uninstall | No write/remove outside the authorized directory |
| Use hardlinked, symlinked or non-regular manifest leaf | Reject before trusting the file |
| Install/update same ID in two processes | Coherent outcome with explicit conflict, no lost update |
| Revoke permission concurrently with an update | Revocation persists; stale update cannot silently restore the grant |
| Disk-full or crash during state save | No partial state interpreted as authorization |
| Remove or disable a plugin while a UI action is queued | Current-state resolution denies stale dispatch |
| Reuse v1 manifest on a v2 host | Valid original cards and links remain supported |
| Submit schema 2 with an unknown API major | Reject incompatible API; no implicit downgrade |
| Submit RTMPS key, traversal or encoded-separator URL | Reject invalid preset; no automatic streaming |
| Request ui.notifications or notification fields in v1/v2 | Reject as unsupported schema capability |
| Submit v3 notifications with unknown event or executable/url fields | Reject invalid declaration, with no toast or callback |
| Send host transition after notification permission revocation | No toast from the revoked plugin |
| Restore an already-active connection on startup | No artificial connected notification |

Inspect both method results and final on-disk state after each run. A
successful JSON validation proves schema acceptance, not cross-process
atomicity or filesystem race safety.

## Compatibility fixtures and public publication

The [public contract cases](../tests/fixtures/manifest-contract.json)
cover both schema versions, API major 1, permission constraints, SemVer
rules, DNS restrictions, canonical provider URLs and path traversal.
JSON Schema handles structure; the SDK validator enforces additional
semantic URL constraints. The v1 manifest fields remain unchanged.

Latest v1 and v2 schemas reject numeric SemVer prerelease components
with leading zeros, matching the host parser. Historical release tags
remain available and unchanged.

V3 extends the same host API major (1) with opt-in static in-app toast rules
for four event transitions. The host must enforce event allowlists and grants
at dispatch, render text literally and never pass session payloads to plugins.
The number of visible toasts should remain bounded across all installed
plugins, not merely per-manifest.

Before releasing new SDK metadata, run public fixture/validator tests and
both examples in CI, and publish documentation, manifests and schemas
only. No private host source, signing keys, tokens, user credentials, stream
keys or executable artifacts should be included.

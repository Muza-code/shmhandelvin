# Market Center data archives

Dated snapshots under `archive/market-center/YYYY-MM-DD/` preserve a fixed, restore-ready view of the source files, crawl checkpoints, observations, derived data, and published market dataset.

## Snapshot for 2026-11-02

- Snapshot manifest: [manifest.json](market-center/2026-11-02/manifest.json)
- Source commit: `7aeb1357d9760c06dbd9a0273903606b45fe21ba`
- The manifest records each original path, archived path, Git blob SHA, and byte size.
- The archived paths reference the same Git blobs captured at the source commit. Later edits to live files do not change this dated snapshot.

To restore a file, copy it from the matching path under the dated snapshot back to its original path. For the complete project state as of this archive, use the source commit recorded in the manifest.

Do not edit a dated snapshot in place. After a completed data refresh, create a new date-stamped snapshot and manifest.

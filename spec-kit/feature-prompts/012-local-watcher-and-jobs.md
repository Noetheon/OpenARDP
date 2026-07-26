# Feature 012 — Local watcher and stable jobs

## Goal
Watch opt-in roots and schedule one stable bounded ingest per meaningful change.

## Requirements
Debounce/stability windows, deduplication/fencing, cancellation, backpressure, retry policy, rename/delete/tombstone semantics, symlink/network-share rules, crash recovery, foreground-first CLI, structured redacted events and no implicit parent traversal. Overflow or missed-event recovery requires bounded rescan.

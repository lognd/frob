+++
id = "01M42SQ7RJ5T8SJWKRHYV9D5RT"
title = "State store read fails with PermissionDenied on Windows while a concurrent write replaces the entry"
type = "bug"
category = "in-progress"
priority = "high"
points = 1
reporter = "lognd"
created = "2026-10-04T06:30:47Z"
updated = "2026-10-04T06:34:32Z"
scope = ["crates/gob-trust/src/state/**", "crates/gob-trust/tests/state.rs"]

[[acceptance]]
text = "Given concurrent writers and a reader on Windows, when the reader reads during a replace, then it gets a hit or a miss and never an error, across 20 consecutive runs on nova-windows"
bound = true
+++

CI runs 37182219626 and 37181044823 (windows-latest, intermittent): gob-trust::state concurrent_writers_never_expose_a_torn_entry fails because StateStore::get returns Io{op: read} PermissionDenied (os error 5) while another writer renames a new entry over it; Windows denies opens of a file in the replace or delete-pending window, Linux never does. Real users with concurrent frob processes would hit it. Treat PermissionDenied (and sharing violations) on read as transient: retry with a short bounded backoff, then report a Miss (the caller recomputes) rather than an error; never surface a torn entry.

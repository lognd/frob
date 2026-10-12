+++
id = "01M4DPJR7RFS40YTGVT80A3EXX"
title = "gob-walk path-only mode; crunk-ingest parses files in parallel; CRLF policy for crunk fix"
type = "task"
category = "done"
outcome = "done"
priority = "low"
points = 2
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-08T12:07:33Z"
updated = "2026-10-11T17:11:21Z"
scope = ["changelog.d/**", "crates/gob-walk/**", "crates/crunk-ingest/**"]

[[acceptance]]
text = "Given the ungoverned scan, when run, then no file is hashed or read through the content source (gob_walk::walk_paths lists paths and sizes only)"
bound = true

[[acceptance]]
text = "Given many CSS files plus an unreadable one, when ingested via the parallel load-then-place path, then sheets and diagnostics keep path order and stats are exact (ordering and determinism only; parallel speed-up is not asserted)"
bound = true
+++

Follow-ups from ~HRHS033.

+++
id = "01M4DPJR7RFS40YTGVT80A3EXX"
title = "gob-walk path-only mode; crunk-ingest parses files in parallel; CRLF policy for crunk fix"
type = "task"
category = "in-progress"
priority = "low"
points = 2
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-08T12:07:33Z"
updated = "2026-10-11T04:09:02Z"
scope = ["changelog.d/**", "crates/gob-walk/**", "crates/crunk-ingest/**"]

[[acceptance]]
text = "Given the ungoverned scan, when run, then no file is hashed or read through the content source (gob_walk::walk_paths lists paths and sizes only)"
bound = true

[[acceptance]]
text = "Given many CSS files, when ingested, then they are parsed in parallel and sheets, diagnostics and stats are identical to the sequential order"
bound = false
+++

Follow-ups from ~HRHS033.

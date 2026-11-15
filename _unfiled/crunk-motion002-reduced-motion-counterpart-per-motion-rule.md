+++
id = "01M7EXTD9FSV02JDTP3008DWFE"
title = "crunk MOTION002: reduced-motion counterpart per motion rule"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:24Z"
updated = "2026-11-15T06:20:24Z"
idempotency_key = "crunkplan-261468c78256"
labels = ["no-story"]

[[acceptance]]
text = "a motion without a reduced counterpart raises MOTION002"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding M3.
Evidence: no reduced-motion pairing check
Remedy: require a prefers-reduced-motion counterpart
Crates/files: crates/crunk-rules motion
Verify against HEAD first; the audit ran on a stale binary.

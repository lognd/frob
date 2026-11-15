+++
id = "01M7EXTZ8P6TDJ2XDZ0CC61EV0"
title = "crunk parity: local crunk parity verb and fix stale CI module doc"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:42Z"
updated = "2026-11-15T06:20:42Z"
idempotency_key = "crunkplan-58a696f0ad99"
labels = ["no-story"]

[[acceptance]]
text = "crunk parity runs the solver parity check locally"
bound = false

[[acceptance]]
text = "module doc no longer mentions a CI job"
bound = false
+++

Source: /home/logan/projects/frob-audit-grimble-crunk.md, finding H3.
Evidence: no local parity verb; parity.rs line 5 still says The CI parity
Remedy: add a verb running the gallery parity check; correct the doc
Crates/files: crates/crunk/src, crates/crunk-gallery/src/parity.rs:5
Verify against HEAD first; the audit ran on a stale binary.

+++
id = "01M7EXTGZAGT7GWQ5CPYE9QD7Y"
title = "crunk serve: host serve_patch with --write and read tools"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:27Z"
updated = "2026-11-15T06:20:27Z"
idempotency_key = "crunkplan-dd295a36dbf2"
labels = ["no-story"]

[[acceptance]]
text = "crunk serve lists render, snapshot and explain tools"
bound = false

[[acceptance]]
text = "patch tool is absent without --write"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding L5.
Evidence: serve patch tool is dead code with no serve verb; also grimble-crunk L3. Related epic ~Z20JD5Q
Remedy: register crunk serve reusing gob-serve; --write enables patch; expose render, snapshot, explain read tools
Crates/files: crates/crunk/src/serve_patch.rs, crates/crunk/src
Verify against HEAD first; the audit ran on a stale binary.

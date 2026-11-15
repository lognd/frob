+++
id = "01M7EXRF3QCRR8SRZWK8J1ABWG"
title = "crunk render: fix E-GALLERY-NOT-BUILT remedy text and exit code"
type = "task"
category = "todo"
priority = "medium"
points = 1
parent = "01M7ETK794J40RVB9YAWNQ6NF3"
reporter = "lognd"
created = "2026-11-15T06:19:20Z"
updated = "2026-11-15T06:19:20Z"
idempotency_key = "crunkplan-a12ee1bca722"
labels = ["no-story"]

[[acceptance]]
text = "the error remedy names a command or feature that exists"
bound = false

[[acceptance]]
text = "exit code matches the documented refusal class (test)"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding L3.
Evidence: E-GALLERY-NOT-BUILT exits 3 and prints a remedy that cannot work in the default build
Remedy: print a remedy that works (feature flag or alternative verb) and use a usage-class exit code
Crates/files: crates/crunk/src/render.rs:387, crates/crunk/tests/it/render_solve.rs:95
Verify against HEAD first; the audit ran on a stale binary.

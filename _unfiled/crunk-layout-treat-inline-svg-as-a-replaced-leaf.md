+++
id = "01M7EXTF0NB5JZ2QX4MC1F0JE0"
title = "crunk-layout: treat inline svg as a replaced leaf"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:25Z"
updated = "2026-11-15T06:20:25Z"
idempotency_key = "crunkplan-9388ec55731a"
labels = ["no-story"]

[[acceptance]]
text = "a scene with inline svg solves (test)"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding M9.
Evidence: inline svg makes a scene unsolvable
Remedy: treat svg as a replaced leaf with intrinsic size
Crates/files: crates/crunk-layout/src/style/tree.rs:74-90
Verify against HEAD first; the audit ran on a stale binary.

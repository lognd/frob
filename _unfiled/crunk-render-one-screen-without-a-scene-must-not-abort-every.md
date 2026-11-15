+++
id = "01M7EXTGQS38Y4PC7B6FN71FWM"
title = "crunk render: one screen without a scene must not abort every cell"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:27Z"
updated = "2026-11-15T06:20:27Z"
idempotency_key = "crunkplan-2f1ac565aaa5"
labels = ["no-story"]

[[acceptance]]
text = "render of a project with one scene-less screen renders the rest"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding L4.
Evidence: render aborts all cells when one screen lacks a scene
Remedy: skip with a per-cell Unresolved
Crates/files: crates/crunk/src/render.rs
Verify against HEAD first; the audit ran on a stale binary.

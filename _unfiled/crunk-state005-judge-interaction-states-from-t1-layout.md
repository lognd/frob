+++
id = "01M7EXTBWQSWSD3P7827D76424"
title = "crunk STATE005: judge interaction states from T1 layout solves"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:22Z"
updated = "2026-11-15T06:20:22Z"
idempotency_key = "crunkplan-62fd6a883646"
labels = ["no-story"]

[[acceptance]]
text = "a component state with a differing solve is judged by STATE005"
bound = false

[[acceptance]]
text = "missing per-state scene is Unresolved with a reason"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding M2.
Evidence: interaction states are only names; STATE is Unresolved with no per-state scene
Remedy: solve a scene per state and compare boxes/tokens in STATE005
Crates/files: crates/crunk-rules state rules, crates/crunk-layout
Verify against HEAD first; the audit ran on a stale binary.

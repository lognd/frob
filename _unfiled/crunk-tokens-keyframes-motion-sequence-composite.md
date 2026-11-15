+++
id = "01M7EXSEJRK1EV3WXJA4333KXE"
title = "crunk tokens: keyframes / motion-sequence composite"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M7ETKA6EFEZGRH2DMQBD8818"
reporter = "lognd"
created = "2026-11-15T06:19:52Z"
updated = "2026-11-15T06:19:52Z"
idempotency_key = "crunkplan-007470e26f02"
labels = ["no-story"]

[[acceptance]]
text = "a keyframes composite exports to css @keyframes (snapshot)"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding H7.
Evidence: no composite for multi-step animations
Remedy: add a keyframes composite
Crates/files: crates/crunk-tokens, crates/crunk-export
Verify against HEAD first; the audit ran on a stale binary.

+++
id = "01M7EXSDRS69DDPD4B5TQCCSZX"
title = "crunk tokens: gradient, angle and string token types"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M7ETKA6EFEZGRH2DMQBD8818"
reporter = "lognd"
created = "2026-11-15T06:19:51Z"
updated = "2026-11-15T06:19:51Z"
idempotency_key = "crunkplan-f14a1d7c408d"
labels = ["no-story"]

[[acceptance]]
text = "a gradient token round trips spec -> css export"
bound = false

[[acceptance]]
text = "an invalid angle is a typed error"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding H7.
Evidence: no token type for gradients, angles or strings
Remedy: add the three types to crunk-tokens with exporters
Crates/files: crates/crunk-tokens, crates/crunk-export
Verify against HEAD first; the audit ran on a stale binary.

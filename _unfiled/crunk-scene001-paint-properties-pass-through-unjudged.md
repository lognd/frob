+++
id = "01M7EXSDANMZNYFBNFM3ANT5NJ"
title = "crunk SCENE001: paint properties pass through unjudged"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M7ETKA6EFEZGRH2DMQBD8818"
reporter = "lognd"
created = "2026-11-15T06:19:51Z"
updated = "2026-11-15T06:19:51Z"
idempotency_key = "crunkplan-605a5c4096b7"
labels = ["no-story"]

[[acceptance]]
text = "a scene with a literal background colour is flagged"
bound = false

[[acceptance]]
text = "a token-backed paint passes"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding H7.
Evidence: paint properties (background, filter, shadow) are not validated against tokens in scenes
Remedy: judge paint properties in SCENE001 against token kinds
Crates/files: crates/crunk-rules scene rules
Verify against HEAD first; the audit ran on a stale binary.

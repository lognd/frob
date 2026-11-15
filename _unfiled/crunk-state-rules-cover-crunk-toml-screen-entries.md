+++
id = "01M7EXTCVT791T51NS9XF8Q7T0"
title = "crunk STATE rules: cover crunk.toml [[screen]] entries"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:23Z"
updated = "2026-11-15T06:20:23Z"
idempotency_key = "crunkplan-26f7429a64b2"
labels = ["no-story"]

[[acceptance]]
text = "a [[screen]] missing a required state raises a finding"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding M2.
Evidence: STATE rules skip [[screen]] entries
Remedy: extend STATE rules to screens
Crates/files: crates/crunk-rules state
Verify against HEAD first; the audit ran on a stale binary.

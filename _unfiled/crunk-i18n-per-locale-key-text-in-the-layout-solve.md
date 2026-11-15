+++
id = "01M7EXTEBAJFVRKJ74TBJGWWVW"
title = "crunk i18n: per-locale key text in the layout solve"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:25Z"
updated = "2026-11-15T06:20:25Z"
idempotency_key = "crunkplan-66664a2078fa"
labels = ["no-story"]

[[acceptance]]
text = "a longer German string overflows and is reported (test)"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding M8.
Evidence: solve uses one string per key
Remedy: solve per locale and report overflow
Crates/files: crates/crunk-layout, crates/crunk-spec content
Verify against HEAD first; the audit ran on a stale binary.

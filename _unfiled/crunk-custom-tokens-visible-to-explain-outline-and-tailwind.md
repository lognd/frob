+++
id = "01M7EXTF9ESMBNVM3WG85RNKPA"
title = "crunk: custom tokens visible to explain, outline and tailwind export"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:26Z"
updated = "2026-11-15T06:20:26Z"
idempotency_key = "crunkplan-96f3d39e3e95"
labels = ["no-story"]

[[acceptance]]
text = "a custom token appears in explain, outline and the tailwind export"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding M10.
Evidence: custom tokens are invisible to explain/outline/tailwind
Remedy: include custom tokens in all three paths; re-test on a fresh build first
Crates/files: crates/crunk explain/outline, crates/crunk-export tailwind
Verify against HEAD first; the audit ran on a stale binary.

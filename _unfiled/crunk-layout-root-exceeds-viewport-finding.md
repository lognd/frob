+++
id = "01M7EXSJ4P91S7J04SNVHNS5D8"
title = "crunk layout: root-exceeds-viewport finding"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M7ETKAPM2000N80NA0W5NAM5"
reporter = "lognd"
created = "2026-11-15T06:19:56Z"
updated = "2026-11-15T06:19:56Z"
idempotency_key = "crunkplan-69deb3568827"
labels = ["no-story"]

[[acceptance]]
text = "a 2000px root at 1280 viewport raises a finding"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding H8.
Evidence: overflowing root is not reported
Remedy: emit a finding when the root box exceeds the viewport
Crates/files: crates/crunk-rules layout
Verify against HEAD first; the audit ran on a stale binary.

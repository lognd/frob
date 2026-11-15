+++
id = "01M7EXSHPSJ1X15V94A94K2SXJ"
title = "crunk layout: data-copy text substitution before measuring"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M7ETKAPM2000N80NA0W5NAM5"
reporter = "lognd"
created = "2026-11-15T06:19:55Z"
updated = "2026-11-15T06:19:55Z"
idempotency_key = "crunkplan-e54cc619e0bf"
labels = ["no-story"]

[[acceptance]]
text = "a long copy string in data-copy makes the solved box wider than placeholder (test)"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding H8.
Evidence: placeholder text is measured, not the real copy
Remedy: substitute data-copy content before text measurement
Crates/files: crates/crunk-layout, crates/crunk-ingest scene
Verify against HEAD first; the audit ran on a stale binary.

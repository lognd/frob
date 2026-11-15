+++
id = "01M7EXSJVHZRXWZAQEZS6ZZMBP"
title = "crunk SCENE: flag literal px in scene styles"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M7ETKAPM2000N80NA0W5NAM5"
reporter = "lognd"
created = "2026-11-15T06:19:57Z"
updated = "2026-11-15T06:19:57Z"
idempotency_key = "crunkplan-a8eafeb476d5"
labels = ["no-story"]

[[acceptance]]
text = "literal px in a scene style raises a finding"
bound = false

[[acceptance]]
text = "token-backed values do not"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding H8.
Evidence: literal px in scene styles bypass tokens
Remedy: SCENE rule flags literal lengths
Crates/files: crates/crunk-rules scene
Verify against HEAD first; the audit ran on a stale binary.

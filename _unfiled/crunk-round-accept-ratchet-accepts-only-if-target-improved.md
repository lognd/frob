+++
id = "01M7EXW3G109HC2JZKJCTVXWR8"
title = "crunk round accept: ratchet accepts only if target improved and no family regressed"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M7ETB5ZJ7M2A2XGWZTYVYHHX"
reporter = "lognd"
created = "2026-11-15T06:21:19Z"
updated = "2026-11-15T06:21:19Z"
idempotency_key = "crunkplan-7bed367ae8f4"
labels = ["no-story"]

[[acceptance]]
text = "a regressing round restores the last accepted state (test)"
bound = false

[[acceptance]]
text = "an improving round is appended to rounds.jsonl"
bound = false
+++

Source: /home/logan/projects/frob-research-ui.md, section T5.
Remedy: record rounds in .crunk/rounds.jsonl; restore last accepted state otherwise; cap about 6 rounds, keep best
Crates/files: crates/crunk new verb
Keep any new heuristic advisory and dated; a clean run means no known defect, not quality.

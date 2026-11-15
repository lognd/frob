+++
id = "01M7EXTHSYPCDGP9VN2P28FR5V"
title = "crunk nits: tokens -q envelope, gob_walk WARN, outline font case"
type = "task"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-15T06:20:28Z"
updated = "2026-11-15T06:20:28Z"
idempotency_key = "crunkplan-a0fb1c9fa1f6"
labels = ["no-story"]

[[acceptance]]
text = "tokens -q prints nothing"
bound = false

[[acceptance]]
text = "missing design/scenes emits no WARN"
bound = false

[[acceptance]]
text = "outline preserves font family case"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding L8.
Evidence: tokens -q prints the envelope; gob_walk WARN on missing design/scenes; outline lowercases font families
Remedy: fix all three
Crates/files: crates/crunk tokens/outline
Verify against HEAD first; the audit ran on a stale binary.

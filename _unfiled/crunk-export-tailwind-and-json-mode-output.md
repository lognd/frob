+++
id = "01M7EXSA3HAHC7JAYH0NYR4ZD1"
title = "crunk export: tailwind and json mode output"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M7ETK97Q5VJ027ZV8AFBJWRQ"
reporter = "lognd"
created = "2026-11-15T06:19:48Z"
updated = "2026-11-15T06:19:48Z"
idempotency_key = "crunkplan-554fbe88d92c"
labels = ["no-story"]

[[acceptance]]
text = "tailwind and json exports carry every declared mode (snapshot)"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding H5.
Evidence: tailwind and json exports lose modes
Remedy: emit modes in tailwind theme and json output
Crates/files: crates/crunk-export tailwind/json
Verify against HEAD first; the audit ran on a stale binary.

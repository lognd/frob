+++
id = "01M7EXS9R6SHNQ9SH8NN87B0DN"
title = "crunk export css: emit a block per mode with opt-in media mapping"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M7ETK97Q5VJ027ZV8AFBJWRQ"
reporter = "lognd"
created = "2026-11-15T06:19:47Z"
updated = "2026-11-15T06:19:47Z"
idempotency_key = "crunkplan-a69aaf56ee61"
labels = ["no-story"]

[[acceptance]]
text = "css export contains a block per declared mode (snapshot)"
bound = false

[[acceptance]]
text = "with the media option off, no @media rule is emitted"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding H5.
Evidence: css export has one value per token
Remedy: emit [data-theme] or :root blocks per mode; opt-in prefers-color-scheme mapping
Crates/files: crates/crunk-export css
Verify against HEAD first; the audit ran on a stale binary.

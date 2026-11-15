+++
id = "01M7EXSAC09004R5215ZYG9KKW"
title = "crunk EXPORT rule: declared mode absent from a target"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M7ETK97Q5VJ027ZV8AFBJWRQ"
reporter = "lognd"
created = "2026-11-15T06:19:48Z"
updated = "2026-11-15T06:19:48Z"
idempotency_key = "crunkplan-d8996c079670"
labels = ["no-story"]

[[acceptance]]
text = "a target missing a declared mode raises a finding"
bound = false

[[acceptance]]
text = "targets carrying all modes raise none"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding H5.
Evidence: no check that a target carries every mode
Remedy: EXPORT rule flags a declared mode a target omits
Crates/files: crates/crunk-rules export
Verify against HEAD first; the audit ran on a stale binary.

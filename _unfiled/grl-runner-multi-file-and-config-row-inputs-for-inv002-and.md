+++
id = "01M4XK7SFTNE6JAK4WZZDJXFY5"
title = "GRL runner: multi-file and config-row inputs for INV002 and DOC002 (link/heading kinds)"
type = "task"
category = "todo"
priority = "medium"
points = 8
reporter = "lognd"
created = "2026-10-14T16:16:59Z"
updated = "2026-10-28T12:56:07Z"
labels = ["no-story"]
scope = ["crates/gob-plan/src/**", "crates/gob-symbols/src/**"]

[[acceptance]]
text = "INV002 and DOC002 corpus examples pass via run_example"
bound = false
+++

Found while working ~YJPYE5V: INV002 needs path-aware model_of_source (gob-symbols names every example file example.<ext>) plus config rows matched by i.file.path; DOC002 needs link/heading kinds, cross-file file domain, resolve(...), a second file input and a multi-model executor. Runner still returns Unsupported for second file, model, fixed.

no-story: internal engineering task in gob-plan; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.

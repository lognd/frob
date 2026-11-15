+++
id = "01M7EXWMX8JXX95YD42D416JT7"
title = "crunk direction roll --seed: pick among passing directions outside the model"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M7ETB68V756QR7EDQ8FBNYGR"
reporter = "lognd"
created = "2026-11-15T06:21:37Z"
updated = "2026-11-15T06:21:37Z"
idempotency_key = "crunkplan-065bcad29363"
labels = ["no-story"]

[[acceptance]]
text = "the same seed gives the same direction (test)"
bound = false

[[acceptance]]
text = "failing directions are never picked"
bound = false
+++

Source: /home/logan/projects/frob-research-ui.md, section T6a.
Remedy: seeded deterministic selection among directions that pass checks
Crates/files: crates/crunk new verb
Keep any new heuristic advisory and dated; a clean run means no known defect, not quality.

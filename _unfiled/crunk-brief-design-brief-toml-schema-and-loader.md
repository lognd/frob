+++
id = "01M7EXVEHMREJCTMW69H8RZ5FM"
title = "crunk brief: design/brief.toml schema and loader"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M7ETB54NC45Z1NN143S2KCRQ"
reporter = "lognd"
created = "2026-11-15T06:20:58Z"
updated = "2026-11-15T06:20:58Z"
idempotency_key = "crunkplan-ccc8f0441b20"
labels = ["no-story"]

[[acceptance]]
text = "a valid brief.toml parses into the model"
bound = false

[[acceptance]]
text = "unknown or malformed fields give a typed error"
bound = false
+++

Source: ~/projects/frob-research-ui.md, section T1.
Remedy: add Brief model (subject, audience, job, world, [[reference]] with take/leave, [[anti_reference]], category_default, predictable_opposite, signature, register, voice) and loader
Crates/files: crates/crunk-spec
Keep any new heuristic advisory and dated; a clean run means no known defect, not quality.

+++
id = "01M7EXTHK222S2SYK3ET8FKH30"
title = "crunk fonts: implement fonts.toml"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:28Z"
updated = "2026-11-15T06:20:28Z"
idempotency_key = "crunkplan-eb242b5bffae"
labels = ["no-story"]

[[acceptance]]
text = "a face listed in fonts.toml is used by the solve"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding L7.
Evidence: fonts.toml is specified but not implemented
Remedy: load fonts.toml and register faces with the solver
Crates/files: crates/crunk-layout, crates/crunk-spec
Verify against HEAD first; the audit ran on a stale binary.

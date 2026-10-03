+++
id = "01M4069R5RH6KRMMNQA76XZ8VG"
title = "frob milestone new, add and show with --criterion"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:53Z"
updated = "2026-10-03T07:08:24Z"
idempotency_key = "m2-rel-milestone-verbs"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-pm/src/milestone/**", "crates/frob/src/milestone_cmd.rs", "crates/frob/src/lib.rs"]

[[links]]
kind = "blocked-by"
target = "01M4069QWSJEH5KW8K0YR8CA0D"

[[acceptance]]
text = "Given a version and goal, when frob milestone new runs, then the object exists with its criteria unbound"
bound = false

[[acceptance]]
text = "Given an epic, when frob milestone add runs, then show lists it and a repeat returns already true"
bound = false
+++

Verbs `frob milestone new VERSION --goal --target --criterion (repeatable)`, `frob milestone add EPIC VERSION`, `frob milestone show VERSION` with --json envelope; version must be semver; repeat is a no-op (already: true).

+++
id = "01M4D6NEQYAZEFFX3P0S2EJV2N"
title = "gob-check: run external tool stages concurrently with the in-process stages (cargo stages grouped by target lock)"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T07:29:24Z"
updated = "2026-10-09T20:39:52Z"
scope = ["changelog.d/**", "crates/gob-check/src/tools.rs", "crates/gob-check/src/pipeline.rs", "crates/frob-check/tests/check.rs"]

[[acceptance]]
text = "Given frob check warm on this repository, when timed, then wall time is below the sum of stage times and per-stage timing is still reported"
bound = true
+++

notes/research/profile-2026-10-07.md section 5 item 3 (tools.rs:331 runs tools serially: 6.0 s of 6.8-7.8 s warm).

+++
id = "01M4D6NB00MBEV0PRHN15CXZP8"
title = "Performance: fixes from the 2026-10-07 command profile (69 leaves)"
type = "epic"
category = "todo"
priority = "high"
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T07:29:20Z"
updated = "2026-10-08T07:29:20Z"

[[acceptance]]
text = "Given cargo dev profile in CI, when it runs, then frob check warm, ticket doctor, cycle velocity, board, doctor and land are within their budgets"
bound = false
+++

notes/research/profile-2026-10-07.md sections 3-5; budgets in crates/gob-dev/profile.toml (~RWD03DW). Outcome: every everyday verb under its budget in debug and release.

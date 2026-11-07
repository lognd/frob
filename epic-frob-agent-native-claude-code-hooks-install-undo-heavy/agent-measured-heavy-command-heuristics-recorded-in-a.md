+++
id = "01M4P2N1XMDZAGS1EAZPR6WQMQ"
title = "agent: measured heavy-command heuristics recorded in a checked profile, recommend heavy for historically heavy commands"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M4P2MQ9EDGX3NCSBRS0H1AYB"
reporter = "lognd"
created = "2026-10-11T18:12:27Z"
updated = "2026-11-07T06:38:24Z"
labels = ["no-story"]
scope = ["crates/frob-cli/**", "crates/frob/**", "crates/frob-tests/**", "crates/frob-check/**", "docs/guides/hooks.md", "docs/reference/**", "heavy-profile.toml", "docs/README.md", "docs/schemas/config.json"]

[[acceptance]]
text = "durations and peak disk growth of verbs and commands are recorded to telemetry"
bound = true

[[acceptance]]
text = "a heavy profile (committed, checked by frob check) lists commands over configured wall-time or disk thresholds, derived from telemetry"
bound = true

[[acceptance]]
text = "pre-bash recommends or routes through heavy for commands in the profile"
bound = true

[[acceptance]]
text = "profile refresh is deterministic and a stale profile is a check finding"
bound = true
+++

no-story: internal engineering task in frob-cli; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.

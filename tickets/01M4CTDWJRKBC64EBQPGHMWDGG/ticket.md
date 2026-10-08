+++
id = "01M4CTDWJRKBC64EBQPGHMWDGG"
title = "land: refuse onto a base whose latest CI run is red, through frob-gh (audit H1)"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T03:55:33Z"
updated = "2026-10-08T07:23:19Z"
scope = ["changelog.d/**", "crates/frob-land/**", "crates/frob-gh/**", "docs/design/tickets.md", "docs/reference/config.md", "docs/schemas/config.json"]

[[acceptance]]
text = "Given a base whose latest CI run failed, when frob land runs, then it refuses with E-LAND-BASE-RED naming the run url"
bound = true

[[acceptance]]
text = "Given an unreadable CI state, when frob land runs, then the outcome follows the configured policy and is reported as Unresolved, never green"
bound = true
+++

notes/review/audit-2026-10-07.md H1. 20 lands went onto a red Windows base for 30 hours. Gate land on the base tip's latest CI conclusion via frob-gh; red refuses with E-LAND-BASE-RED naming the run; unknown follows [release] require_ci semantics (Unresolved, configurable); --override --reason records an event.

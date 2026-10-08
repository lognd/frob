+++
id = "01M4CTDWJRKBC64EBQPGHMWDGG"
title = "land: refuse onto a base whose latest CI run is red, through frob-gh (audit H1)"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T03:55:33Z"
updated = "2026-10-08T03:55:33Z"
scope = ["changelog.d/**", "crates/frob-land/**", "crates/frob-gh/**"]

[[acceptance]]
text = "Given a base whose latest CI run failed, when frob land runs, then it refuses with E-LAND-BASE-RED naming the run url"
bound = false

[[acceptance]]
text = "Given an unreadable CI state, when frob land runs, then the outcome follows the configured policy and is reported as Unresolved, never green"
bound = false
+++

notes/review/audit-2026-10-07.md H1. 20 lands went onto a red Windows base for 30 hours. Gate land on the base tip's latest CI conclusion via frob-gh; red refuses with E-LAND-BASE-RED naming the run; unknown follows [release] require_ci semantics (Unresolved, configurable); --override --reason records an event.

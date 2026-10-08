+++
id = "01M4CT016NKN4QRVY0Y57FX1J2"
title = "Sprint gate: frob work refuses a ticket outside the active cycle unless expedite or --unplanned --reason"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-08T03:47:59Z"
updated = "2026-10-08T05:42:53Z"
scope = ["crates/frob-pm/**", "crates/frob-cli/**", "crates/frob/**", "docs/design/pm-enforcement.md", "changelog.d/**", "crates/frob-worktree/**", "crates/frob-check/**", "docs/reference/**", "docs/schemas/**", "frob.toml", "docs/design/architecture.md", "crates/gob-time/**"]

[[acceptance]]
text = "Given an active cycle and a standard ticket outside it, when frob work runs, then it is refused with E-PM-NOT-IN-CYCLE and the hint names cycle assign and --unplanned"
bound = true

[[acceptance]]
text = "Given --unplanned --reason, when frob work runs, then the ticket joins the active cycle as an over-commit with the reason and starts"
bound = true

[[acceptance]]
text = "Given an expedite ticket outside the cycle, when frob work runs, then it starts"
bound = true
+++

Scrum: work comes from the sprint backlog. When a cycle is active and [pm] sprint_gate = true (new knob, default true for repositories with cycles, materialized by frob init), work/start refuses a ticket that is not a member of the active cycle (E-PM-NOT-IN-CYCLE), except class expedite; --unplanned --reason TEXT assigns it to the active cycle as an over-commit with the reason recorded in the event, so unplanned work is visible in the retro and the commitment ratio. pm-enforcement.md gets the rule.

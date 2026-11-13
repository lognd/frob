+++
id = "01M7AYFADBZEDS3BQQNE0AN3EV"
title = "warnings: burn down acks and coverage findings (EXC016 EXC005 COV001 COV004 SYS013 CAP001 AFFECT001)"
type = "chore"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-13T17:14:51Z"
updated = "2026-11-13T20:48:29Z"
labels = ["no-story"]
scope = ["crates/**"]

[[acceptance]]
text = "Zero unresolved findings for EXC016, EXC005, COV001, COV004, SYS013, CAP001, AFFECT001 in frob check."
bound = true
+++

From CI: EXC016 16, EXC005 13, COV001 14, COV004 3, SYS013 12, CAP001 22, AFFECT001 1. Add tests or frob:tests, run frob ack after re-reading, fix real issues.

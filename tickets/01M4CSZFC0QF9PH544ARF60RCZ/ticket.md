+++
id = "01M4CSZFC0QF9PH544ARF60RCZ"
title = "PM036 overdue cycle: an active cycle past its end date fires, and frob work refuses to start new work until it is closed"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-08T03:47:26Z"
updated = "2026-10-08T03:47:26Z"
scope = ["crates/frob-pm/**", "crates/frob-cli/**", "crates/frob/**", "docs/design/pm-enforcement.md", "changelog.d/**"]

[[acceptance]]
text = "Given an active cycle whose end date has passed, when frob check runs, then PM036 fires naming the cycle and the days overdue"
bound = false

[[acceptance]]
text = "Given an overdue active cycle, when frob work starts a standard ticket, then it is refused with E-PM-CYCLE-OVERDUE; an expedite ticket still starts"
bound = false
+++

2026-10-07: cycle ~VCCMDF6 ended 2026-10-05 and stayed active for two days while about 70 tickets landed outside any cycle; nothing fired. Add PM036 (Warning, Error under [pm] strict) when today > end of an active cycle, and make the work/start gate refuse with E-PM-CYCLE-OVERDUE (teaching message: close it with frob cycle close --retro) unless the ticket is expedite. Record in pm-enforcement.md section 8 table.

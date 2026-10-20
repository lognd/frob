+++
id = "01M4CTE4TWJP2W6EV2PZN62TQN"
title = "crunk applies exceptions (crunk-check/src/product.rs 78) and gob-check owns binding (audit M4)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T03:55:42Z"
updated = "2026-10-10T23:36:58Z"
scope = ["changelog.d/**", "crates/crunk-check/**", "crates/gob-check/**"]

[[acceptance]]
text = "Given a COLOR001 finding covered by a crunk:waive comment with a reason, when crunk check runs, then it is reported in report.suppressed with that reason and is absent from the open findings"
bound = true

[[acceptance]]
text = "Given a crunk:waive comment without a reason, when crunk check runs, then nothing is suppressed and WAIVE001 fires"
bound = true
+++

notes/review/audit-2026-10-07.md M4.

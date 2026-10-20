+++
id = "01M4P0SXRPC9QT51PXGV9ZJ9AA"
title = "dup ratchet: tighten T1 and T2 from warn to error and shrink the baseline"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4P0SQC82NJ7DV5BC3CAR5Y4"
reporter = "lognd"
created = "2026-10-11T17:40:09Z"
updated = "2026-10-11T17:40:09Z"

[[acceptance]]
text = "T1 and T2 severity is error by default after a one-cycle warn burn-in"
bound = false

[[acceptance]]
text = "Baseline entry count is lower than at T0 landing, or each remaining entry has a justifying ticket"
bound = false

[[acceptance]]
text = "Docs and generated rule pages updated"
bound = false
+++

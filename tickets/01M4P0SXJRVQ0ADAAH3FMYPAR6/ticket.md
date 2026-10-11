+++
id = "01M4P0SXJRVQ0ADAAH3FMYPAR6"
title = "dup T2: whole-repo near-miss clone scan as CI/nightly job with baseline ratchet"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4P0SQC82NJ7DV5BC3CAR5Y4"
reporter = "lognd"
created = "2026-10-11T17:40:09Z"
updated = "2026-10-11T17:40:09Z"

[[acceptance]]
text = "CI job runs off the critical path and never blocks land"
bound = false

[[acceptance]]
text = "Baseline file records existing clusters; only new clusters fail"
bound = false

[[acceptance]]
text = "Runtime budget documented and measured on this repository"
bound = false
+++

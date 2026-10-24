+++
id = "01M4P3HCCJG2YN2M39FXJAFC5D"
title = "evidence: bind a test that measures the check warm-run median (15s target) for the speed cache"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-11T18:27:55Z"
updated = "2026-10-24T03:47:53Z"
scope = ["crates/frob-tests/**"]

[[acceptance]]
text = "a test measures warm frob check median on a fixture and fails above the 15s target"
bound = true
+++

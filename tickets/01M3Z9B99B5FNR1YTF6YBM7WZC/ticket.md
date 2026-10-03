+++
id = "01M3Z9B99B5FNR1YTF6YBM7WZC"
title = "frob land E-LAND-CHECK-RED lists warnings instead of the blocking findings"
type = "bug"
category = "in-progress"
priority = "medium"
points = 1
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:46:55Z"
updated = "2026-10-03T03:07:46Z"
idempotency_key = "m2-land-msg"
labels = ["milestone:2"]
scope = ["crates/frob-land/**"]

[[acceptance]]
text = "Given a land blocked by one error among many warnings, when the refusal is printed, then the error is listed first and warnings are only counted"
bound = false
+++

When the land check is red, the refusal message enumerates the first ten findings regardless of severity, so a land blocked by one TOOL001 error showed ten COV001 warnings and hid the cause. List only the findings at or above fail_on (and required Unresolved), blocking first, with the count of the rest.

+++
id = "01M3ZX7EG6S2V48F43HP1GM2NQ"
title = "Plan format: typed plan IR, serialization, full validation of untrusted bytes"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:20Z"
updated = "2026-10-04T04:37:59Z"
idempotency_key = "m2-plan-format"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/src/plan/**", "crates/gob-plan/src/lib.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX779NSRZ97ZQM5DP3BZJZ"

[[acceptance]]
text = "Given a plan value, when serialized and read back, then it is equal and carries provenance, polarity, needs and the prefilter kind set"
bound = true

[[acceptance]]
text = "Given truncated, out-of-range or cyclic plan bytes from disk, when loaded, then validation returns an Err naming the reason and never panics"
bound = false
+++

Implements plugins.md sections 3 and 6; security.md section 2.2 (plan bytes from disk).

The one plan format run by the executor, carrying pack provenance, polarity, needs, prefilter kind set and cost class. Bytes from disk are always fully validated; unchecked access only for include_bytes! embedded plans.

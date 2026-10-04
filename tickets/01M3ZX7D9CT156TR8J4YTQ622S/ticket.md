+++
id = "01M3ZX7D9CT156TR8J4YTQ622S"
title = "GRL error goldens GRL001-GRL015 written before the compiler"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:19Z"
updated = "2026-10-04T04:34:27Z"
idempotency_key = "m2-grl-goldens"
labels = ["milestone:2", "area:grl", "kind:test"]
scope = ["crates/gob-plan/tests/grl_errors/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX779NSRZ97ZQM5DP3BZJZ"

[[acceptance]]
text = "Given a fixture directory with one case per GRL001-GRL015 and the GRL016 expected-versus-actual diff, when the golden harness runs, then every case is discovered and a case whose checker has not landed is reported pending by code, never skipped silently"
bound = true

[[acceptance]]
text = "Given a landed checker for a code, when its golden is enabled and the output differs by one byte, then the harness fails and prints the diff"
bound = false
+++

Implements grl-spec.md sections 10 and 13.2.

Design the compiler messages first: one fixture per code (input .grl plus the expected rustc-style rendering with code, span, help and explain lines) and a harness that lists them. Each checker ticket enables its own codes.

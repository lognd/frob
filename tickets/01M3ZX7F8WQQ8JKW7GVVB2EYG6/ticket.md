+++
id = "01M3ZX7F8WQQ8JKW7GVVB2EYG6"
title = "Example runner: fire, clean, unresolved, notapplicable, known-gap, fixed"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:21Z"
updated = "2026-10-03T03:34:21Z"
idempotency_key = "m2-grl-examples"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/src/examples/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7DMYNTWB3AP04CDMAECH"

[[links]]
kind = "blocked-by"
target = "01M3ZX7F1SGDAFM6ZQ8BP7TEN3"

[[acceptance]]
text = "Given an example with `//~ warn` on line 3 of a Rust input, when run, then it passes iff exactly one warn finding is reported on line 3"
bound = false

[[acceptance]]
text = "Given a known-gap example that starts firing, when run, then it fails with GRL016 and a diff, and a mismatching fire example prints the expected and actual findings"
bound = false
+++

Implements grl-spec.md section 9.

Examples are tests: comment-marker expectations per language (//~ warn, #~ error, --~, <!--~ -->), expect lines for comment-less languages, file/config/model/diff/lease sub-blocks, known-gap flips to failure, fixed asserts fix output; GRL016 prints the expected-versus-actual diff.

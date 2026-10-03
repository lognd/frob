+++
id = "01M40P6CWYKN4V9HEBRXR3342F"
title = "nextest evidence: a filter expression with | is refused as matching no tests"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T10:50:40Z"
updated = "2026-10-03T11:02:43Z"
idempotency_key = "m2-evidence-filter-union"
labels = ["milestone:2", "release:0.532.0"]
scope = ["crates/frob-evidence/**"]

[[acceptance]]
text = "Given --ref with -E 'test(a) | test(b)' where both tests exist, when evidence add runs, then both run and a measured pass is recorded"
bound = true

[[acceptance]]
text = "Given a filter that matches nothing, when evidence add runs, then it still refuses"
bound = true
+++

Found on ~MVY3DFK: ticket evidence add --provider nextest --ref="-p gob-plan -E 'test(a) | test(b)'" was refused with E-EVIDENCE-NO-TESTS although both tests exist; substring filters worked. Either the --ref value is split on whitespace or shell-tokenized in a way that breaks the -E expression, or the zero-match detection (~PFY7RCD, matched_no_tests) misreads nextest's output for union expressions. Reproduce with a two-test project, find which, fix it, and test: a union -E expression records a measured pass; a genuinely empty match still refuses. Document how --ref is tokenized for the nextest provider (shell-words? one argument?) in the provider's docs and in cli.md.

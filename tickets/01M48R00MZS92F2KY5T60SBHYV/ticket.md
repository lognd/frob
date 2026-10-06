+++
id = "01M48R00MZS92F2KY5T60SBHYV"
title = "One applicability resolver from applies and the capability matrix (behaviour-preserving)"
type = "story"
category = "done"
outcome = "done"
priority = "high"
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-10-06T13:56:04Z"
updated = "2026-10-06T23:19:08Z"
scope = ["crates/gob-check/**", "crates/frob-obligations/**"]

[[links]]
kind = "blocked-by"
target = "01M48R002DA5FKCXDP8HQ6B02X"

[[acceptance]]
text = "the existing status.rs unit table passes unchanged against resolve"
bound = true

[[acceptance]]
text = "verdict reasons appear in check JSON and text"
bound = true

[[acceptance]]
text = "need_of is deleted"
bound = true
+++

M2: resolve(applies, file facts) -> Examine | NotApplicable | Unresolved replaces need_of, Need, RuleNeed and the internals of subject_status_for; the opaque-text row keeps today's answers (the D106 flip is ~59MXB7Z, after this). Verdict reasons reach the check JSON. Supersedes ~YPRBJPF. Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.

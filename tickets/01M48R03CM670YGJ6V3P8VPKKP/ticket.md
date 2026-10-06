+++
id = "01M48R03CM670YGJ6V3P8VPKKP"
title = "Migrate frob-ledger, frob-pm, frob-release, frob-lease and gob-config rules to the two-file shape"
type = "story"
category = "todo"
priority = "medium"
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-10-06T13:56:07Z"
updated = "2026-10-06T13:56:07Z"
scope = ["crates/frob-ledger/**", "crates/frob-pm/**", "crates/frob-release/**", "crates/frob-lease/**", "crates/gob-config/**"]

[[links]]
kind = "blocked-by"
target = "01M48R029HFBJ3PKQX5GBBKJ6V"

[[acceptance]]
text = "frob check JSON identical before and after"
bound = false

[[acceptance]]
text = "PM rules' inapplicable reasons appear in the NotApplicable list"
bound = false
+++

M6b: ledger and PM shared work via a memoised context. Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.

+++
id = "01M48R02V2J0R5ZXWP9MXXGNZ3"
title = "Migrate frob-obligations, frob-ack and frob-tests rules to the two-file shape"
type = "story"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M48QZYWAMKC7MXHQ6AYNV7BN"
reporter = "lognd"
created = "2026-10-06T13:56:06Z"
updated = "2026-10-17T21:46:32Z"
scope = ["crates/frob-obligations/**", "crates/frob-ack/**", "crates/frob-tests/**", "crates/frob-check/**", "crates/gob-mdtest/coverage-allowlist.toml", "docs/reference/rules/**"]

[[links]]
kind = "blocked-by"
target = "01M48R029HFBJ3PKQX5GBBKJ6V"

[[acceptance]]
text = "frob check JSON on this repository is identical before and after"
bound = true

[[acceptance]]
text = "the file-rules stage is not more than 10 percent slower (--timing)"
bound = false
+++

M6a. Design: docs/design/rule-authoring.md (D107); detail and the failure table: notes/research/rule-authoring.md section 4.

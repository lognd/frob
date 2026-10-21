+++
id = "01M4CXR89ERNB60CEDG60E2DXH"
title = "Screen spec files extend [[screen]]: states, platforms, landmarks, copy keys, status and content hash; STATE001-006"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4CXR6ER06SRMEJGSZ20JD5Q"
reporter = "lognd"
created = "2026-10-08T04:53:39Z"
updated = "2026-10-21T05:31:02Z"
scope = ["changelog.d/**", "crates/crunk-spec/**", "crates/crunk-check/**", "crates/crunk-rules/**", "docs/crunk/**", "docs/schemas/crunk.json", "docs/reference/rules/AFFECT001.md", "docs/reference/rules/BP001.md", "docs/reference/rules/BP002.md", "docs/reference/rules/BP003.md", "docs/reference/rules/CAP001.md", "docs/reference/rules/CAP002.md", "docs/reference/rules/CFG001.md", "docs/reference/rules/CI001.md", "docs/reference/rules/CI003.md", "docs/reference/rules/CI006.md", "docs/reference/rules/CI007.md", "docs/reference/rules/CI010.md", "docs/reference/rules/CI014.md", "docs/reference/rules/CLAIM001.md", "docs/reference/rules/CLAIM003.md", "docs/reference/rules/COLOR001.md", "docs/reference/rules/COLOR002.md", "docs/reference/rules/CONTRAST001.md", "docs/reference/rules/COV001.md", "docs/reference/rules/COV003.md"]

[[acceptance]]
text = "Given a screen spec, when checked, then STATE coverage and status hash rules apply and old [[screen]] tables still load"
bound = false
+++

docs/design/crunk.md section 2.

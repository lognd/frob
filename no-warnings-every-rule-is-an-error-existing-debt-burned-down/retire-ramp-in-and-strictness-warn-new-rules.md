+++
id = "01M5XMJHEVEF3774EFRMBFZHZD"
title = "Retire ramp-in and strictness warn-new-rules"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M5XETK612GJ5QZZZXBA6CSGY"
reporter = "lognd"
created = "2026-10-27T02:56:01Z"
updated = "2026-10-27T02:56:01Z"
scope = ["crates/gob-rules/src/ramp*"]

[[acceptance]]
text = "ramp, effective_ramped, ramp_product_findings, new_rule_warn_releases removed from frob, grimble and crunk checks"
bound = false

[[acceptance]]
text = "strictness accepts strict only; the old value is ignored with a deprecation note"
bound = false
+++

Implements docs/design/rules.md section 6.1 (rules.md 6.1.3). Filed from ~ZHW5Y2M.

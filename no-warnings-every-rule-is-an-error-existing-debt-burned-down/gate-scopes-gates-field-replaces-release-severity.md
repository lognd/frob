+++
id = "01M5XMJHVMJH25WGPDQRC646Y4"
title = "Gate scopes: gates field replaces release_severity"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M5XETK612GJ5QZZZXBA6CSGY"
reporter = "lognd"
created = "2026-10-27T02:56:02Z"
updated = "2026-10-27T02:56:02Z"
scope = ["crates/gob-rules/**"]

[[acceptance]]
text = "rules declare gates subset of local|ci|release; HUMAN001/HUMAN002 are release-only Errors and not run at local or ci"
bound = false

[[acceptance]]
text = "release_severity removed from RuleDef, gate_severity and apply_gate; check --gate selects the gate, CI auto-detected"
bound = false
+++

Implements docs/design/rules.md section 6.1 (rules.md 6.1.5). Filed from ~ZHW5Y2M.

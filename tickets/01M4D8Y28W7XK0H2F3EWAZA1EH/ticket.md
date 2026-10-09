+++
id = "01M4D8Y28W7XK0H2F3EWAZA1EH"
title = "gob-check: SARIF 2.1.0 tool parser with a per-tool id map and source_rule"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M4D8X558Q07HCMEBP224NQP4"
reporter = "lognd"
created = "2026-10-08T08:09:03Z"
updated = "2026-10-09T16:34:50Z"
scope = ["changelog.d/**", "crates/gob-check/**"]

[[acceptance]]
text = "Given a SARIF log with results, suppressions and an unknown ruleId, when the stage runs, then mapped results become frob findings with source_rule, suppressed results are visible to EXC017, the unknown id falls back to TOOL002 and unreadable output is a required TOOL001 Unresolved"
bound = true
+++

notes/research/lint-catalogue-2026-10-08.md 3.1 E1 and 4.2 N01: enables rows U01, U04 and K32 (Roslyn, Microsoft.Unity.Analyzers and PublicApiAnalyzers emit SARIF). rules.md 4 id-map pattern.

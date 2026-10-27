+++
id = "01M5G4YPZX0N4W0ZZSFG6YQBDT"
title = "Rules that never emit Unresolved keep a kind=unresolved allowlist entry"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-21T21:12:56Z"
updated = "2026-10-27T02:58:36Z"
scope = ["crates/gob-mdtest/coverage-allowlist.toml"]
+++

Found while closing ~C5DQ4WJ. These frob rules cannot be driven to an Unresolved finding by an mdtest block, so their kind=unresolved allowlist entries stay until the product changes: CFG001 (gob_config::check returns Result; doctor logs skipped), CI001 CI003 CI006 CI007 CI010 CI014 and TOOL002 (tool failures are attributed to TOOL001 in gob-check tools stage_findings), EXC014 EXC016 EXC017 (declared Error/Warn only), GRL016 PERF001 PROC001 TICK008 TICK009 (Error findings only; an Unresolved appears only from an internal evaluation failure), DSL001 DSL002 DSL003 PARSE001 PARSE002 (directive scan emits Error/Warn only). Either give each a real Unresolved path (and a case) or declare them never-unresolved in rule meta so the coverage gate stops requiring the kind. Also: COV001 csharp/text/island matrix cells disagree with the derivation (legacy cov001 emits Warn for csharp and nothing for text or island); tracked by the existing matrix_gap tickets.

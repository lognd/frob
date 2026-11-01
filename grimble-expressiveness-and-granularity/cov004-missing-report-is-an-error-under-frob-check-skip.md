+++
id = "01M6ACP6D0C91GJK12H9B9301B"
title = "COV004 missing-report is an error under frob check --skip-tools when the tool is installed"
type = "bug"
category = "todo"
priority = "high"
points = 3
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-11-01T01:48:20Z"
updated = "2026-11-01T01:48:20Z"
idempotency_key = "cov004-skip-tools"
scope = ["crates/frob-obligations/src/coverage.rs", "crates/frob-check/**", "crates/gob-check/**"]

[[acceptance]]
text = "Under skip-tools a language with tests but no coverage report is Unresolved (not run), not an Error, with a test; without skip-tools the Error is unchanged"
bound = false
+++

CI ubuntu frob check (cargo run -p frob-cli -- check --skip-tools) reports 'csharp has tests but no coverage report' as an error because dotnet is installed on the runner. skip-tools means coverage was not run, so it should be Unresolved like python/rust. Plumb the skip flag to missing_reports in crates/frob-obligations/src/coverage.rs.

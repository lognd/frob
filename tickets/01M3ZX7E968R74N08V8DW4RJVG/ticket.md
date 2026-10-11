+++
id = "01M3ZX7E968R74N08V8DW4RJVG"
title = "Fix applicability: machine, maybe-incorrect, has-placeholders, manual"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M3ZX76ZV963F3AXRKJ8F744N"
reporter = "lognd"
created = "2026-10-03T03:34:20Z"
updated = "2026-10-11T22:06:38Z"
idempotency_key = "m2-diag-applicability"
labels = ["milestone:2", "area:diagnostics"]
scope = ["crates/gob-rules/src/finding.rs", "crates/gob-rules/src/meta.rs", "crates/gob-diagnostics/src/record.rs", "crates/gob-rules/tests/ui.rs", "crates/gob-rules/tests/ui/fix_missing_applicability.rs", "crates/gob-rules/Cargo.toml", "crates/gob-diagnostics/src/lib.rs", "crates/gob-diagnostics/tests/contract.rs", "crates/frob-check/tests/check.rs", "crates/frob-obligations/src/tick_paths.rs", "crates/gob-directives/src/compat.rs", "crates/gob-check/src/fix.rs", "crates/gob-check/src/store.rs", "crates/gob-rules/src/lib.rs", "crates/gob-diagnostics/tests/snapshots/contract__json_success_snapshot.snap", "crates/gob-rules/tests/ui/fix_missing_applicability.stderr", "docs/schemas/envelope.json", "docs/schemas/sibling.json", "Cargo.lock"]

[[acceptance]]
text = "Given a finding with a Deterministic fix, when serialized to JSON, then its fixes entry has applicability machine and the exact edits"
bound = true

[[acceptance]]
text = "Given a fix constructed without an applicability, when compiled, then it does not compile or is a typed error (no default)"
bound = true
+++

Implements diagnostics.md section 3.

Add Applicability to Fix and map the existing FixKind (Manual, Deterministic, VerifyCommit, FixIt) onto it; JSON findings carry fixes with applicability and the exact text edits. Applicability is required, no default.

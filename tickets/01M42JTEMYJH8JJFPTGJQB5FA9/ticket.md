+++
id = "01M42JTEMYJH8JJFPTGJQB5FA9"
title = "Make frob-evidence escape_line and escape_non_ascii thin wrappers over gob-diagnostics::escape"
type = "chore"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-04T04:30:12Z"
updated = "2026-10-04T04:30:12Z"
scope = ["crates/frob-evidence/Cargo.toml", "crates/frob-evidence/src/attestation.rs"]

[[acceptance]]
text = "Given the two escapers, when frob-evidence calls them, then they delegate to gob_diagnostics and no second copy exists"
bound = false
+++

found while working ~PJH50MJ: the shared escaper now lives in gob-diagnostics/src/escape.rs; frob-evidence/Cargo.toml was leased by ~EDPHHFS so the dedupe was deferred. Add the gob-diagnostics dependency and make attestation::escape_line / escape_non_ascii re-export or wrap it; keep their existing tests.

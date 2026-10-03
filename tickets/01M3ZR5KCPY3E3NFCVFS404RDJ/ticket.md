+++
id = "01M3ZR5KCPY3E3NFCVFS404RDJ"
title = "Cross-crate call resolution through use imports and crate dependencies; field and signature tables"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T02:05:57Z"
updated = "2026-10-03T03:08:08Z"
idempotency_key = "m2-cov-crosscrate"
labels = ["milestone:2"]
scope = ["crates/gob-symbols/**", "crates/frob-obligations/**", "docs/reference/fidelity.md"]

[[acceptance]]
text = "Given this repository, when frob check runs, then COV001 Unresolved findings are below 40 and a test proves no genuinely ambiguous call became Covered"
bound = false
+++

Carries the unmet target of ~EHMQCXV: COV001 Unresolved on this repository below 40 (284 after that ticket). Resolve path calls across crates soundly through use imports (use frob_ack::Inputs; Inputs::collect resolves to that crate's associated function when exactly one exists) and the Cargo dependency closure already parsed in frob-obligations deps.rs; build a struct field type table so self.field.method() is typed; record method signatures (self kind, arity) so unknown-receiver calls admit only methods whose arity matches. Every change must keep soundness: anything still ambiguous stays May or Unknown, never Covered.

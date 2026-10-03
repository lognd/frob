+++
id = "01M3ZTB2Y0J454GSSK4KGAMSF9"
title = "gob-ir: shared resolution cache keyed by (scope, name)"
type = "task"
category = "done"
outcome = "done"
priority = "low"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T02:43:54Z"
updated = "2026-10-03T03:38:46Z"
idempotency_key = "m2-gobir-scope-name-cache"
labels = ["milestone:2", "perf"]
scope = ["crates/gob-ir/**"]

[[acceptance]]
text = "Given 20k unresolved references at scope depth 10000, when resolved cold, then the time is within 2x of the depth-200 case and the equivalence snapshot is unchanged"
bound = false
+++

Follow-up of ~7QWX8P1. resolve(RefId) memoizes per reference, so many unresolved references at the bottom of a very deep scope chain cost O(refs x scopes) on first resolution. Add a shared cache keyed by (scope, name) and skip scopes that are transparent for a name (no matching declaration, no covering hint, single Must edge). Invalidate with the existing edge/declare/opaque mutation hooks. Keep the equivalence snapshot (tests/equivalence.rs) byte-identical and add a bench case: 20k unresolved refs at depth 10k.

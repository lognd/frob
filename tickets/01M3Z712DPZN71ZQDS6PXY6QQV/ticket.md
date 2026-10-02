+++
id = "01M3Z712DPZN71ZQDS6PXY6QQV"
title = "gob-ir: U terms, scope graph with status, canonical facet stream, queries, Kleene evaluator"
type = "task"
category = "todo"
priority = "high"
points = 13
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:23Z"
updated = "2026-10-02T21:06:23Z"
idempotency_key = "m2-ir"
labels = ["milestone:2"]
scope = ["crates/gob-ir/**"]

[[acceptance]]
text = "Given two alpha-equivalent terms, when printed and hashed, then the output and every facet digest are identical"
bound = false

[[acceptance]]
text = "Given a rule predicate over a term containing an opaque node in its dependency cone, when evaluated, then the answer is Unknown and a P+ rule yields an Unresolved finding"
bound = false
+++

universal-model.md sections 2-5 and 7 (D56, D62): Tm(Sigma_U + Sigma_L) with the thirteen universal operators and adapter operators, stable identities with content as a facet, locations as an address sort, the scope graph with Must/May/Unknown edges, alpha-normal printer, canonical facet stream for Sig/Body/Doc/Attr/Contract, the syntactic queries of Theorem 2 as a library, the answer lattice types (Exact/Bounds/Unknown/NotApplicable, Must/May/Unknown) and a stratified-Datalog-style evaluator with Kleene semantics and rule polarity, the atom registry and callee vocabulary as inventory entries. Layering: gob-languages < gob-ir < gob-symbols. Property tests for alpha-invariance and determinism; a corpus of hand-written U terms.

+++
id = "01M4E0BVMZHYZYC7PHEA0YWS08"
title = "GRL017 misses negative positions: def bodies reset the negation count, def call sites under not do not carry it, count bodies under < or == and earlier report when clauses are not treated as negative"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
parent = "01M4CXTT0JWKFTX1HBB703QA80"
reporter = "lognd"
created = "2026-10-08T14:58:33Z"
updated = "2026-10-10T15:47:40Z"
scope = ["changelog.d/**", "crates/gob-plan/**", "docs/design/grl-spec.md"]

[[acceptance]]
text = "Given `not d(f)` where def d contains `certainly` or `possibly` at even depth, when compiled, then GRL017 fires; a def body with `not` inside it still fires; `d(f)` outside any negation stays clean"
bound = true

[[acceptance]]
text = "Given `count(...)` with `certainly` or `possibly` in its body compared with `<`, `<=`, `==` or `!=`, when compiled, then GRL017 fires; `>` and `>=` stay clean"
bound = true

[[acceptance]]
text = "Given a `report ... when C` clause that has a later `report` clause, when compiled and C holds `certainly` or `possibly`, then GRL017 fires; the last `report`'s `when` stays clean"
bound = true

[[acceptance]]
text = "Docs (grl-spec 7.0.4) state the def, count and report-when negative positions"
bound = false
+++

Found by the grl-spec 7.0 draft (2026-10-08). Example: not d(f) with certainly inside d passes.

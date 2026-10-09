+++
id = "01M4E0BVMZHYZYC7PHEA0YWS08"
title = "GRL017 misses negative positions: def bodies reset the negation count, def call sites under not do not carry it, count bodies under < or == and earlier report when clauses are not treated as negative"
type = "bug"
category = "todo"
priority = "high"
points = 2
parent = "01M4CXTT0JWKFTX1HBB703QA80"
reporter = "lognd"
created = "2026-10-08T14:58:33Z"
updated = "2026-10-08T14:58:33Z"
scope = ["changelog.d/**", "crates/gob-plan/**"]

[[acceptance]]
text = "Given each listed form, when compiled, then GRL017 fires with the span of the certainly or possibly"
bound = false
+++

Found by the grl-spec 7.0 draft (2026-10-08). Example: not d(f) with certainly inside d passes.

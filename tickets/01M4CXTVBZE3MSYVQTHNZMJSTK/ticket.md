+++
id = "01M4CXTVBZE3MSYVQTHNZMJSTK"
title = "gob-ir: an Unknown or unclassified edge widens hi to the frontier instead of being dropped (formal review H1)"
type = "bug"
category = "done"
outcome = "done"
priority = "critical"
class = "expedite"
points = 3
parent = "01M4CXTT0JWKFTX1HBB703QA80"
reporter = "lognd"
created = "2026-10-08T04:55:04Z"
updated = "2026-10-08T06:23:01Z"
scope = ["changelog.d/**", "crates/gob-ir/**"]

[[acceptance]]
text = "Given the two H1 scenarios, when evaluated, then the verdict is Unknown, never a definite answer"
bound = true

[[acceptance]]
text = "Given strata with poisoned derivations, when evaluated, then the poison propagates to dependent strata"
bound = true
+++

notes/review/formal-review-2026-10-08.md H1 and section 4 item 1: eval/ctx.rs 293 and 310 read an Unknown resolution as no edge; eval/program.rs 309 discards derivation poison. A call through an unresolved alias can be certified no-cycle (Pc) and a P- rule can fire 'no test reaches f' when one does.

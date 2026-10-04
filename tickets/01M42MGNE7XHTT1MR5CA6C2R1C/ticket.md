+++
id = "01M42MGNE7XHTT1MR5CA6C2R1C"
title = "A rule that fails to evaluate yields zero findings instead of a required Unresolved; a corrupt index makes frob check exit 0 clean"
type = "bug"
category = "todo"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-04T04:59:49Z"
updated = "2026-10-04T04:59:49Z"
scope = ["crates/frob-check/src/**"]

[[acceptance]]
text = "Given a corrupt ledger index, when frob check runs, then it reports required Unresolved findings naming the failed rules and the gate fails"
bound = false
+++

Reproduced: with a corrupt ticket index every ticket verb fails yet frob check exits 0 with zero findings; about 10 sites in product.rs and snapshot.rs swallow evaluation errors. Unknown is never a pass. Evidence and repro: notes/review/v1-gap/D-incidents.md (P-05).

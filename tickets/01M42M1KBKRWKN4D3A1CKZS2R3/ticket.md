+++
id = "01M42M1KBKRWKN4D3A1CKZS2R3"
title = "ticket close --outcome done succeeds while the ticket branch holds unmerged commits; doctor stays green"
type = "bug"
category = "in-progress"
priority = "critical"
points = 3
reporter = "lognd"
created = "2026-10-04T04:51:35Z"
updated = "2026-10-04T04:51:56Z"
scope = ["crates/frob-evidence/src/done.rs", "crates/frob-evidence/src/guard.rs", "crates/frob/src/ticket/**", "crates/frob/tests/close_guards.rs", "crates/frob-ledger/src/doctor.rs", "docs/design/tickets.md"]

[[acceptance]]
text = "Given a ticket branch with an unmerged commit, when ticket close --outcome done runs, then it refuses naming the unmerged commits and the remedy (land or --no-land --reason)"
bound = false

[[acceptance]]
text = "Given a ledger with a done ticket whose branch has unmerged commits, when ticket doctor runs, then it reports it"
bound = false

[[acceptance]]
text = "Given a ticket landed through land, when it closes, then the guard passes"
bound = false
+++

Reproduced by the v1 gap analysis (notes/review/v1-gap/C-features.md P-01; also A PT-3 and B PT-1, v1 T-4052): in a throwaway repository, frob ticket close --outcome done succeeds while ticket/<handle> has a commit not merged into the base, and ticket doctor reports nothing. This is v1's 'done but absent' incident class: a ticket recorded done whose change never reached the base. Fix: the done guard (one place, alongside done_requires) refuses outcomes done and fixed when the ticket branch has commits not reachable from the base, unless the work landed through land (which merges first) or --no-land --reason is given and recorded; ticket doctor flags every done ticket whose branch has unmerged commits, and a done ticket whose scope paths show no change on the base since it started with no evidence of an intentional empty change. Outcomes wont-fix, duplicate and invalid are exempt (~8RZK7QV).

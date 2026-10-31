+++
id = "01M4KW3A47K7S9WGD3NBVVPJB4"
title = "frob lease widen grows the lease scope to diff files no other lease holds (and check --ticket --widen)"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
reporter = "Claude"
created = "2026-10-10T21:39:25Z"
updated = "2026-10-31T07:54:50Z"
persona = "an agent holding a lease"
capability = "widen my lease to files no other lease holds"
outcome_text = "I can finish a ticket without a manual requeue"
scope = ["crates/frob/src/lease_cmd.rs", "crates/frob-lease/**", "crates/frob-check/**", "changelog.d/**", "crates/frob/tests/it/lease_widen.rs", "docs/design/tickets.md"]

[[acceptance]]
text = "Given a ticket whose diff touches a file outside its scope that no other lease holds, when frob lease widen (or check --ticket with --widen) runs, then the scope grows to that file with a ledger event"
bound = true
+++

Split from ~B3S3XGJ (criterion 2): the change lives in the frob binary and frob-check, outside that ticket's lease.

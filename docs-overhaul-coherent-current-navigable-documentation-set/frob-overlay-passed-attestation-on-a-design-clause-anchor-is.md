+++
id = "01M6BYM5XMG4WD49JAQXZR3S4S"
title = "frob overlay: passed attestation on a design clause anchor is the pass verdict of a manual verified_by row"
type = "task"
category = "in-progress"
priority = "low"
points = 3
parent = "01M69J39HA547HNNCMCAMNDCCT"
reporter = "lognd"
created = "2026-11-01T16:21:03Z"
updated = "2026-11-06T12:42:22Z"
labels = ["grimble", "no-story"]
scope = ["crates/frob-ledger/**", "crates/frob-evidence/src/attestation.rs", "crates/frob-evidence/tests/attestation.rs", "crates/frob/src/**", "docs/design/frob/tickets.md"]

[[links]]
kind = "blocked-by"
target = "01M6BYM5SY94EQF1HW4BVFQAVY"

[[acceptance]]
text = "frob's overlay reads a passed attestation carrying that anchor on a live ticket implementing the entity or a design ancestor as the pass verdict of that manual verified_by row (grmb-spec 12.8, D202) (parent AC2)"
bound = true
+++

Child of ~AMNDCCT. Blocked-by parent handle is not used; ordering after the docs child is advisory (wire it once its handle is known).

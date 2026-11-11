+++
id = "01M5EKM0DB2Y27ZQEH74YB3CNA"
title = "ledger: public single-commit multi-event append for mirror proposals"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T06:50:45Z"
updated = "2026-11-11T15:31:07Z"
scope = ["crates/frob-ledger/src/**", "crates/frob-ledger/tests/**", "crates/frob-mirror/**", "docs/design/frob/tickets.md"]

[[acceptance]]
text = "Ledger::append_many appends several event bodies to one ticket as a single ledger commit, with a test; mirror ledger_source commit_proposals uses it"
bound = true
+++

found while working ~ACC0466: TicketSource::commit_proposals promises one ledger commit but Ledger::append commits one event each; commit_events is pub(crate)

+++
id = "01M5EKM0DB2Y27ZQEH74YB3CNA"
title = "ledger: public single-commit multi-event append for mirror proposals"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T06:50:45Z"
updated = "2026-10-27T02:58:35Z"
+++

found while working ~ACC0466: TicketSource::commit_proposals promises one ledger commit but Ledger::append commits one event each; commit_events is pub(crate)

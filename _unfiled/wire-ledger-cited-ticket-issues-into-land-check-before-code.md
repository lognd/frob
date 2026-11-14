+++
id = "01M7BR4JX3EZVXK1A6JD49NB6Q"
title = "Wire Ledger::cited_ticket_issues into land/check before code push"
type = "task"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-11-14T00:43:22Z"
updated = "2026-11-14T02:02:31Z"
labels = ["no-story"]
scope = ["crates/frob-land/**"]

[[acceptance]]
text = "A frob:ticket citation absent from every ledger blocks land and doctor, and cannot be waived."
bound = true
+++

Follow-up of ~D4YR4SJ: the detector exists in frob-ledger doctor.rs but no caller extracts cited ids from the diff.

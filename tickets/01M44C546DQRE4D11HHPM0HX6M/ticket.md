+++
id = "01M44C546DQRE4D11HHPM0HX6M"
title = "Build the triage inbox verbs: ticket triage accept, decline, snooze, duplicate"
type = "story"
category = "in-progress"
priority = "high"
reporter = "lognd"
created = "2026-10-04T21:12:11Z"
updated = "2026-10-04T21:20:51Z"
scope = ["crates/frob-ledger/**", "crates/frob/src/ticket/mod.rs", "crates/frob/src/ticket/triage_cmd.rs", "crates/frob/tests/triage.rs", "docs/design/tickets.md", "docs/design/cli.md", "docs/reference/cli/frob.md"]

[[acceptance]]
text = "Given tickets in triage labelled triage:accepted, when ticket triage accept --label triage:accepted runs, then each moves to todo in one ledger commit and the report lists every ticket"
bound = true

[[acceptance]]
text = "Given a ticket not in triage, when triage accept names it, then it is refused with a remedy"
bound = true

[[acceptance]]
text = "Given a snoozed ticket, when the inbox is listed before its until date, then it is hidden, and after, it is shown"
bound = false
+++

docs/design/tickets.md designs the triage inbox (the triage event with action accept, decline, snooze, duplicate and an until; the verb frob ticket triage accept|decline|snooze|duplicate; tickets.md lines around 135, 428 and 647) but it is not built: ticket update refuses category, so a ticket in triage can never reach todo. 252 imported v1 tickets are waiting, labelled triage:accepted. Build the verb per the design: accept moves triage to todo; decline closes wont-fix with a reason; duplicate closes duplicate with a target and link; snooze hides the ticket from the inbox until a date. Accept takes several tickets or a query (e.g. --label triage:accepted) so a batch is one ledger commit, reports per ticket, and is idempotent. Refuse on tickets not in triage. Add the inbox listing (ticket triage list) if the design has it. Docs and the generated CLI reference in the same change.

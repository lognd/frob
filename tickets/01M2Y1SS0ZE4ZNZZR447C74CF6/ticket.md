+++
id = "01M2Y1SS0ZE4ZNZZR447C74CF6"
title = "frob ticket attach --remove PATH: first-class attachment removal with ledger record cleanup"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "human"
created = "2026-09-20T00:00:00Z"
updated = "2026-09-20T00:00:02Z"
aliases = ["T-5151"]
labels = ["milestone:0.534.0", "component:tickets"]
scope = ["src/frob/tickets/_reporting_attachments.py", "src/frob/app/ticket_runner/_attach_backfill.py", "src/frob/_cli_parsers/_ticket/_closeout.py", "src/frob/app/config.py", "tests/unit/test_draft_finalize_attachments.py", "tests/test_tickets.py", "design/frob.strata", "docs/design/registry/capability-via-ratchet.lock.json"]

[[acceptance]]
text = "given a ticket with one attachment, when frob ticket attach ID --remove PATH runs, then the file is gone, the record is gone, and the ledger commit is made"
bound = false
+++

Measured 2026-09-20: no verb removes an attachment; the owner asked for research attachments to be removed and the only path was a script over the attachments: frontmatter block plus git rm, i.e. a hand-edit of the ledger the ticket-ledger-gotchas lesson forbids. Add --remove PATH (and --remove-all) that deletes the file, drops the Attachment record, and auto-commits like attach does; refuse when the path is referenced by a done-report.

## Reopen log
- 2026-09-22: closed-but-unlanded: a refused drain wrote state=done with land_commit null and no code on dev (T-5256 class)

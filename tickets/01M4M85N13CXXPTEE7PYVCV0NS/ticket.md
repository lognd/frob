+++
id = "01M4M85N13CXXPTEE7PYVCV0NS"
title = "Mirror issue binding store and ticket branch path lookup"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-11T01:10:25Z"
updated = "2026-10-11T02:01:36Z"

[[acceptance]]
text = "Given a ticket on the branch, when its path is asked of the ledger, then it returns the current branch path"
bound = false

[[acceptance]]
text = "Given a mirrored ticket, when the binding is read, then the issue number is returned"
bound = false
+++

Blocks ~ZR1PXXA (frob ticket url). The crate has no store mapping a ticket ULID to its mirrored issue (docs/design/mirror.md 2.1) and no ledger accessor returning a ticket's current path on the ticket branch (layout::branch_ticket_path is only used at write time in ledger.rs). Provide both so url can print the blob URL and the issue URL.

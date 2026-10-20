+++
id = "01M4M85N13CXXPTEE7PYVCV0NS"
title = "Mirror issue binding store and ticket branch path lookup"
type = "task"
category = "done"
outcome = "done"
priority = "low"
points = 3
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-11T01:10:25Z"
updated = "2026-10-11T04:09:36Z"
scope = ["crates/frob-ledger/src/lib.rs", "crates/frob-ledger/src/ledger.rs", "crates/frob-ledger/src/mirror_map.rs", "crates/frob-ledger/tests/layout.rs"]

[[acceptance]]
text = "Given a ticket on the branch, when its path is asked of the ledger, then it returns the current branch path"
bound = true

[[acceptance]]
text = "Given a mirrored ticket, when the binding is read, then the issue number is returned"
bound = true
+++

Blocks ~ZR1PXXA (frob ticket url). The crate has no store mapping a ticket ULID to its mirrored issue (docs/design/mirror.md 2.1) and no ledger accessor returning a ticket's current path on the ticket branch (layout::branch_ticket_path is only used at write time in ledger.rs). Provide both so url can print the blob URL and the issue URL.

+++
id = "01M4DPJJ8J8C8VP9H6EDJG6B4Z"
title = "cycle plan --apply: batch the assignments into one ledger commit"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T12:07:27Z"
updated = "2026-10-08T12:07:27Z"
scope = ["changelog.d/**", "crates/frob-pm/**", "crates/frob-ledger/**"]

[[acceptance]]
text = "Given plan --apply assigning N tickets, when run, then one commit is written"
bound = false
+++

Follow-up from ~D672RXD: 3.4 s, about 0.5 s per ticket.

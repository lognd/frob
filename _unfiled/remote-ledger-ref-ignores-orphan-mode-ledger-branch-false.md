+++
id = "01M7DBQQF1HYMN07N70M9PBT5A"
title = "remote_ledger_ref ignores orphan-mode ledger branch (false CITED-UNPUSHED)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-14T15:45:07Z"
updated = "2026-11-14T16:00:09Z"
labels = ["no-story", "bug"]
scope = ["crates/frob-ledger/**"]

[[acceptance]]
text = "Orphan-mode cited-ticket check compares against origin/<tickets.branch>, not origin/<tickets.ref>"
bound = true
+++

In orphan ref_mode the ledger lives on tickets.branch (frob-tickets) but Ledger::remote_ledger_ref derives origin/<tickets.ref> (origin/experimental), so land gate E-LAND-CITED-MISSING reports E-DOCTOR-CITED-UNPUSHED for every ticket cited in the diff even after the ledger is pushed. Derive the remote twin from the ledger write ref.

+++
id = "01M7DBQQF1HYMN07N70M9PBT5A"
title = "remote_ledger_ref ignores orphan-mode ledger branch (false CITED-UNPUSHED)"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-14T15:45:07Z"
updated = "2026-11-14T15:45:07Z"
labels = ["no-story", "bug"]
+++

In orphan ref_mode the ledger lives on tickets.branch (frob-tickets) but Ledger::remote_ledger_ref derives origin/<tickets.ref> (origin/experimental), so land gate E-LAND-CITED-MISSING reports E-DOCTOR-CITED-UNPUSHED for every ticket cited in the diff even after the ledger is pushed. Derive the remote twin from the ledger write ref.

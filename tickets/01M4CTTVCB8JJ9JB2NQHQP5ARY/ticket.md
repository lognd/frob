+++
id = "01M4CTTVCB8JJ9JB2NQHQP5ARY"
title = "frob migrate v1: a user-facing v1 to v2 import verb (no gob-dev, no source checkout), with the guide reordered"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "high"
points = 5
parent = "01M4CTTPJ00PTDE0A1SE4MJFCF"
reporter = "lognd"
created = "2026-10-08T04:02:38Z"
updated = "2026-10-09T16:28:37Z"
scope = ["changelog.d/**", "crates/gob-dev/**", "crates/frob/**", "crates/frob-ledger/**", "docs/guides/upgrade-from-v1.md", "docs/migration/**"]

[[acceptance]]
text = "Given a v1 repository, when frob migrate v1 runs from the installed binary, then every v1 ticket is imported and committed and ticket doctor reports them"
bound = false

[[acceptance]]
text = "Given docs/guides/upgrade-from-v1.md, when its steps run in order on a v1 fixture, then each succeeds (doc test)"
bound = false
+++

notes/review/adoption-trial-2026-10-07.md HIGH 5: gob-dev import-v1-tickets defaults --selection to frob's own selection file and errors without it; --all is needed and undocumented; ticket doctor reports 0 until commit so init, doctor, commit looks failed; the importer needs a source checkout and a Rust build. Ship the importer in the frob binary (frob migrate v1, design migration.md), default to all tickets, commit as part of the verb, and fix the guide's order. Moving the import code out of gob-dev also removes gob-dev's frob-ledger edge (~M8WETW7).

+++
id = "01M44YYP1SH9VVNAY5A62XMCHN"
title = "frob migrate tickets: import a consumer repository's v1 ledger"
type = "story"
category = "todo"
priority = "high"
parent = "01M44YYN4E7SXWHQB3H7EHD37P"
reporter = "lognd"
created = "2026-10-05T02:40:43Z"
updated = "2026-10-05T02:42:59Z"

[[acceptance]]
text = "Given a v1 tickets directory, when frob migrate tickets --apply runs, then every ticket is in the v2 ledger with its v1 id as an alias and ticket doctor is clean"
bound = false

[[acceptance]]
text = "Given a second run, when it repeats, then nothing changes"
bound = false
+++

migration.md section 1 and 1.1: move the existing v1 ticket importer (gob-dev import-v1-tickets, which this repository used) behind a product verb: ULIDs minted from v1 created dates, namespaced aliases (repo:T-0042), selective open import via a checked-in selection file or all-history mode, sprints to cycles and milestones, privacy and home-path rules through the ledger write path. One importer, not two: gob-dev calls the shared code.

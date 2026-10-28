+++
id = "01M38BCNBW89FR38R94XQJXRV6"
title = "WEBSEC225 reserved id follow-up (password policy family)"
type = "task"
category = "todo"
priority = "low"
points = 2
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-10-28T12:56:05Z"
aliases = ["T-5500"]
labels = ["v1-cluster:B2", "area:grimble", "triage:accepted", "milestone:0.538.0", "no-story"]
scope = ["src/frob/webapp/_websec_password.py"]
+++

found while working T-5353: WEBSEC218-224 used 7 of the reserved WEBSEC218-225 8-id block; WEBSEC225 has no distinct check defined in the ticket body's seven-item corpus and is left unimplemented -- decide and implement, or formally retire the id.

no-story: internal engineering task in src/frob; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.

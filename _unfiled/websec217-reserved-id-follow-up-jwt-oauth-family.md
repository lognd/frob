+++
id = "01M38BCNBRT3NY5ZH0WF0631DG"
title = "WEBSEC217 reserved id follow-up (JWT/OAuth family)"
type = "task"
category = "todo"
priority = "low"
points = 2
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-10-28T12:55:52Z"
aliases = ["T-5496"]
labels = ["v1-cluster:B2", "area:grimble", "triage:accepted", "milestone:0.538.0", "no-story"]
scope = ["src/frob/webapp/_websec_tokens.py"]
+++

found while working T-5352: WEBSEC209-216 used 8 of the reserved WEBSEC209-217 9-id block; WEBSEC217 has no distinct check defined in the ticket body (secrets-committed is SEC001-003's job) and is left unimplemented -- decide and implement, or formally retire the id.

no-story: internal engineering task in src/frob; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.

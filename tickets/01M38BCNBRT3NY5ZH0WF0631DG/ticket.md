+++
id = "01M38BCNBRT3NY5ZH0WF0631DG"
title = "WEBSEC217 reserved id follow-up (JWT/OAuth family)"
type = "task"
category = "triage"
priority = "low"
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-10-04T21:01:17Z"
aliases = ["T-5496"]
labels = ["v1-cluster:B2", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/webapp/_websec_tokens.py"]
+++

found while working T-5352: WEBSEC209-216 used 8 of the reserved WEBSEC209-217 9-id block; WEBSEC217 has no distinct check defined in the ticket body (secrets-committed is SEC001-003's job) and is left unimplemented -- decide and implement, or formally retire the id.

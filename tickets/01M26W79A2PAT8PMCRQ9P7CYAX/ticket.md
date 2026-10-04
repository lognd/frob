+++
id = "01M26W79A2PAT8PMCRQ9P7CYAX"
title = "Clean src/frob docstrings of change-narrative (DOCARCH001)"
type = "story"
flavour = "user_story"
category = "triage"
priority = "medium"
parent = "01M0XNVQXJ1A3FA43N7AA0PAPK"
reporter = "human"
created = "2026-09-11T00:00:00Z"
updated = "2026-09-11T00:00:00Z"
aliases = ["T-4418"]
labels = ["milestone:0.534.0", "v1-cluster:F1"]

[[acceptance]]
text = "Given a full frob check on src/frob, when DOCARCH001 is measured, then its finding count for src/frob is 0"
bound = false
+++

DOCARCH001 measured 146 findings in src/frob on a full check today (2026-09-11). Rewrite each flagged docstring to state WHAT the symbol does, not the change history/ticket narrative behind it; move any narrative worth keeping into the ticket that made the change. Denominator: 146 (src/frob).

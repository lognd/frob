+++
id = "01M407VRHHCEM42DHWAPN12ND1"
title = "Coordinator log: CFM8QB0 format land, ledger repair, session state"
type = "chore"
category = "todo"
priority = "low"
points = 1
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T06:40:12Z"
updated = "2026-10-03T06:40:12Z"
idempotency_key = "m2-coordinator-log-cfm8qb0"
labels = ["milestone:2"]
scope = ["notes/coordinator.md"]

[[acceptance]]
text = "Given notes/coordinator.md, when read, then the status log has the entry and the land rule covers fold changes"
bound = false
+++

Record the ~CFM8QB0 land (worktree binary, doctor --fix 74 reconcile commits first because the new fold made existing tickets drift) and the session state in notes/coordinator.md.

+++
id = "01M5CW03W58HQWBGDANP418XYE"
title = "Fresh clones and CI get a local frob-tickets branch"
type = "task"
category = "in-progress"
priority = "high"
points = 2
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:41Z"
updated = "2026-10-20T15:01:54Z"
idempotency_key = "dt-DT02"

[[acceptance]]
text = "ticket branch init adopts origin's frob-tickets instead of refusing, including a shallow single-branch clone"
bound = false

[[acceptance]]
text = "frob init in orphan mode creates the local ticket branch from origin"
bound = false

[[acceptance]]
text = "ticket doctor --fix creates the missing ticket branch and plain doctor refuses with E-DOCTOR-TICKET-BRANCH-MISSING"
bound = false
+++

init and doctor --fix create it from origin instead of refusing; shallow clones handled. See docs/design/distributed-tickets.md.

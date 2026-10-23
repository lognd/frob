+++
id = "01M5F010Y998BXB67KPZ4T040N"
title = "grimble-ci: CI012 frob verbs versus workflow commands"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-21T10:27:34Z"
updated = "2026-10-23T03:45:18Z"
scope = ["crates/grimble-ci/**"]

[[acceptance]]
text = "Given a workflow that runs a frob verb that does not exist, when grimble-ci analyzes it, then CI012 reports it"
bound = false

[[acceptance]]
text = "Given a workflow whose frob verbs all exist, when grimble-ci analyzes it, then CI012 stays quiet"
bound = false
+++

Deferred from ~8886VJ4: compare frob verbs with the commands workflows run.

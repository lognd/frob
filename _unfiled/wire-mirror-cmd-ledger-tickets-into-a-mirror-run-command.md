+++
id = "01M7A32314FMETC15Y3P16PG85"
title = "Wire mirror_cmd::ledger_tickets into a mirror run command"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-13T09:15:46Z"
updated = "2026-11-13T12:01:47Z"
labels = ["no-story", "creates:crates/frob/src/mirror_cmd.rs"]
scope = ["crates/frob/src/mirror_cmd.rs"]
+++

Follow-up of ~J9NEK8B: ledger_tickets() has no consuming command yet (dead_code expect). Add the mirror run command; remove the expect.

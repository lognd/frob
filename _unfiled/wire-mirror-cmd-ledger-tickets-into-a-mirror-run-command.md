+++
id = "01M7A32314FMETC15Y3P16PG85"
title = "Wire mirror_cmd::ledger_tickets into a mirror run command"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-13T09:15:46Z"
updated = "2026-11-13T12:37:00Z"
labels = ["no-story", "creates:crates/frob/src/mirror_cmd.rs"]
scope = ["crates/frob/src/mirror_cmd.rs", "changelog.d/01M5EKM0HMCYE834CN3J9NEK8B.added.md", "crates/frob/tests/it/mirror_render.rs", "docs/reference/cli/frob.md"]
+++

Follow-up of ~J9NEK8B: ledger_tickets() has no consuming command yet (dead_code expect). Add the mirror run command; remove the expect.

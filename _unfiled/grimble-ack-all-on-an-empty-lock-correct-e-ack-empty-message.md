+++
id = "01M7EXVK1B2D3BER3WMWANHZF2"
title = "grimble ack --all on an empty lock: correct E-ACK-EMPTY message"
type = "task"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-15T06:21:02Z"
updated = "2026-11-15T06:21:02Z"
labels = ["no-story"]

[[acceptance]]
text = "ack --all on an empty lock prints a message that does not ask for --all"
bound = false
+++

Audit: /home/logan/projects/frob-audit2-grimble.md L3. crates/grimble/src/ack.rs:283-287 and crates/gob-lock/src/plan.rs:11 print 'name a symref or path, or pass --all' even when --all was passed.

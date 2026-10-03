+++
id = "01M4052TZJMWSQJGXQN6ZR4N2C"
title = "Neutralise mentions, closing keywords, cross-repository references and task lists in mirrored text"
type = "task"
category = "todo"
priority = "high"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T05:51:38Z"
updated = "2026-10-03T05:51:38Z"
idempotency_key = "m2-mirror2-neutralise"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/github/neutralise.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83T22GTC94BW4PM742G1"

[[acceptance]]
text = "Given text with @user and @org/team, when rendered, then no mention can notify anyone"
bound = false

[[acceptance]]
text = "Given text with 'fixes #12' and 'owner/repo#5', when rendered, then neither closes or links an issue"
bound = false

[[acceptance]]
text = "Given text with '- [ ] item', when rendered, then no task-list checkbox is produced"
bound = false
+++

Implements mirror.md section 3.6 (side effects; MIR-AUD-21, 23).

Mirrored text cannot trigger GitHub side effects: user and team mentions are neutralised, closing keywords (fixes #12) and cross-repository references render as plain text, and no task-list checkboxes are rendered. The exact ASCII form of the neutralisation is chosen here and recorded in docs.

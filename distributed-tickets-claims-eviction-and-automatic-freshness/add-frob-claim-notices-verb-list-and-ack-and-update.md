+++
id = "01M6Q1JHTF77GRJRN0BDE3BN99"
title = "Add frob claim notices verb (list and --ack) and update distributed-tickets.md 4.4"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M5DCZ3PVHP2ZNP9SVYFFQSVP"
reporter = "lognd"
created = "2026-11-05T23:44:14Z"
updated = "2026-11-06T00:34:23Z"
labels = ["no-story"]
scope = ["crates/frob/src/lease_cmd.rs"]
+++

Follow-up of ~JFEYB9S: Workspace::ack_claim_notices exists in frob-worktree; expose it as 'frob claim notices [--ack]' in crates/frob and document acknowledgement in docs/design/frob/distributed-tickets.md 4.4 (blocked by lease P21FHB9 on docs/**).
no-story: follow-up to an already-landed story; no standalone user-visible story.

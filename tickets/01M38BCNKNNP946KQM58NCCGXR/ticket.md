+++
id = "01M38BCNKNNP946KQM58NCCGXR"
title = "Add milestone to TicketTier and StoryFlavour enum (user_story|quality_objective) on Ticket/TicketSpec"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:02Z"
aliases = ["T-5749"]
labels = ["milestone:v0.536.0"]
scope = ["src/frob/tickets/_models.py"]
+++

Add milestone to TicketTier; add StoryFlavour enum (user_story | quality_objective) on Ticket/TicketSpec.

Positive control: a fixture ticket with flavour: quality_objective round-trips through Ticket.model_validate and flavour set on a non-story tier is rejected.

Doc page: docs/modules/tickets-data-storage.md#data-models

Owner decision Q1: a quality-objective story derives its V-model level from the invariant it binds; an explicit level field at filing is optional and wins on conflict.

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).

---
id: T-1544
title: 'Tier-A auto-fix: TICK006 phantom draft citation refile+renumber'
state: queued
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine.py
- src/frob/tickets/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Follow-up from T-1531: when a TICK006 finding names a draft citation absent from both the ledger and archive, refile a real ticket for it and renumber the citation to the new real id. Needs a Tier-A handler that parses the phantom draft id, files a real ticket capturing recoverable context, and rewrites the citation -- T-1125's prose-reference rewrite already handles the case where the draft DOES exist in the ledger.
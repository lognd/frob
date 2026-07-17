---
id: T-0012
title: 'frob ticket renumber: remedy for sequential-id collisions'
state: queued
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
evidence: []
attachments: []
---
frob ticket renumber -- remedy for sequential-id collisions when two agents create tickets concurrently on separate branches and both claim the same T-#### id. Deferred post-0.1.0.
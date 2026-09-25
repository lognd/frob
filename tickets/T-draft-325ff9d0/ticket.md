---
id: T-draft-325ff9d0
title: docker-compose ingestion
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-1f5f5b2d
parent: T-draft-579d39b7
tier: ticket
sprint: sysdesign
runs_last: false
milestone: 0.539.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/lang/_config_compose.py (new)
- tests/fixtures/sysdesign/config-compose/**
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'DOC006 inline waivers: body names files this ticket will create (T-draft-7ee140de)'
  actor: logan
  at: '2026-09-25'
  old_length: 969
  new_length: 1058
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: docker-compose ingestion
kind: feature
tier: leaf
parent: T-SYS-SB
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/lang/_config_compose.py (new), docs/modules/lang.md,
       tests/fixtures/sysdesign/config-compose/**
blocked_by: [T-SYS-B-CONFIGDOC]

Body:

SYSDESIGN-INVENTORY.md sec 2: "docker-compose: NOT FOUND. Zero hits for 'docker-compose'/
'compose.yaml' in src/." Genuine zero-coverage gap.

Acceptance criteria: `frob.lang._config_compose.parse(path) -> list[ConfigDoc]` reads
`services.<name>.{image, ports, environment, depends_on, deploy.resources, restart}` from
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->compose.yaml/docker-compose.yml. Positive-control fixture: tests/fixtures/sysdesign/
config-compose/env-baked-secret-in-service/**.

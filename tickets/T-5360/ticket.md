---
id: T-5360
title: 'COMPLY substrate: required-page and site-signal detector'
state: in-progress
kind: feature
origin: human
created: '2026-09-23'
priority: high
blocked_by:
- T-5302
parent: T-5145
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_comply_substrate.py
- tests/fixtures/webapp/comply1xx/**
- docs/modules/webapp-comply.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/webapp-comply.md
  reason: 'COMPLY substrate module doc, per fan-out brief: one doc per family to avoid
    7-way collision on webapp.md'
  actor: logan
  at: '2026-09-23'
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5360
branch: t-5360
---
Repo-behavior-signal detector: does this repo collect email/use AI on user data/have subscriptions/sell-or-share data/send SMS/embed session-replay-or-pixel/process health data, via manifest+import scan (package.json deps for stripe/twilio/fullstory/hotjar/openai, Python deps similarly) -- drives which COMPLY rules are relevant, mirrors WEBSUB-2's framework detection. Plus a route/sitemap scan for /privacy, /terms, /accessibility page presence keyed off the detected framework's router. Fixture: one repo fixture per signal plus a plain fixture with none.
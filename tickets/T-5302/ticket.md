---
id: T-5302
title: 'webapp rule-family scaffolding: framework detection, fixture layout, strata
  nodes'
state: queued
kind: feature
origin: human
created: '2026-09-22'
priority: high
blocked_by:
- T-5300
parent: T-5140
tier: ticket
sprint: ''
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
- src/frob/webapp/__init__.py
- src/frob/webapp/_detect.py
- src/frob/sql/__init__.py
- tests/fixtures/webapp/**
- design/frob.strata
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: null
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.535.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: v0.535.0
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: ''
  new_value: ''
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: 0.535.0
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
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
---
New src/frob/webapp/__init__.py (mirrors src/frob/perf/__init__.py's docstring-as-map convention) and src/frob/webapp/_detect.py: pure file-presence/content-sniff framework detection (Next/Vite/Django/Flask/FastAPI/Rails/Laravel/SvelteKit/Astro) returning a FrameworkKind StrEnum and detected: frozenset[FrameworkKind]; a Python CLI repo with no detected framework returns the empty set and every WEBSEC/COMPLY/A11Y/SEO/WEBPERF rule short-circuits to 'not relevant', matching the owner directive verbatim. Also stub src/frob/sql/__init__.py (empty package, SQL family lives outside webapp/ since SQL literals appear in non-web code too). OWNER DIRECTIVE: declare frob.webapp and frob.sql as strata nodes in design/frob.strata with their capabilities (SYS100 refuses new modules otherwise) and add both to [arch.layering] in frob.toml -- do this in the SAME leaf, not a follow-up, since every other leaf in this epic imports one of these two packages and SYS100/layering would refuse them otherwise. Positive-control fixture: one fixture dir per framework asserting detect_frameworks(fixture_root) == {ExpectedKind}, plus a plain Python-CLI fixture asserting the empty set. Doc: docs/modules/webapp.md (new, shape of docs/modules/perf.md).
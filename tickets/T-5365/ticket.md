---
id: T-5365
title: 'SEO113-120: spam-policy shape detectors'
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: high
blocked_by:
- T-5364
- T-5303
parent: T-5147
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 5
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
- src/frob/webapp/_seo_spam.py
- tests/fixtures/webapp/seo1xx/spam/**
- tests/unit/test_seo_spam.py
- docs/modules/webapp-seo-spam.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/seo1xx/**
  reason: per-ticket fixture subdir (sibling T-5362 owns crawl/**) plus test file
    and module doc, batched at intake
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/seo1xx/spam/**
  reason: per-ticket fixture subdir (sibling T-5362 owns crawl/**) plus test file
    and module doc, batched at intake
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/test_seo_spam.py
  reason: per-ticket fixture subdir (sibling T-5362 owns crawl/**) plus test file
    and module doc, batched at intake
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/webapp-seo-spam.md
  reason: per-ticket fixture subdir (sibling T-5362 owns crawl/**) plus test file
    and module doc, batched at intake
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
- field: points
  old_value: '5'
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Keyword stuffing (shape-based n-gram repetition, NOT a density threshold per the story's explicit correction), cloaking via user-agent branching, hidden text via CSS (color==background/font-size:0/opacity:0/off-screen-position -- needs CSS grammar, WEBSUB-1b), scaled-content/doorway-page config advisories, framework-default-title detection (Vite/CRA/Next), staging-without-noindex. Fixture per rule id.
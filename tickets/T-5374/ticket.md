---
id: T-5374
title: 'SEO101-112: per-page tags'
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: high
blocked_by:
- T-5364
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
- src/frob/webapp/_seo_tags.py
- tests/fixtures/webapp/seo1xx/tags/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/seo1xx/**
  reason: per-ticket fixture subdir, siblings own seo1xx/spam/** (T-5365) and seo1xx/crawl/**
    (T-5362)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/fixtures/webapp/seo1xx/tags/**
  reason: per-ticket fixture subdir, siblings own seo1xx/spam/** (T-5365) and seo1xx/crawl/**
    (T-5362)
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: points
  old_value: null
  new_value: '5'
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
Unique title/meta-description per route, og:title/og:type/og:image/og:url, canonical link, favicon, JSON-LD LocalBusiness required properties. html-lang cross-refs A11Y104's rule id, not duplicated. Fixture per rule id via 5147-1.
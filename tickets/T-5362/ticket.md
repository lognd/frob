---
id: T-5362
title: 'SEO121-127: crawl/discovery config'
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: high
blocked_by:
- T-5302
parent: T-5147
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
- src/frob/webapp/_seo_crawl.py
- tests/fixtures/webapp/seo1xx/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
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
robots.txt malformed/Google-Extended decision-record, sitemap.xml schema validation against the sitemaps.org structure, llms.txt advisory-only presence, hreflang, canonical for query-string variants. robots.txt is line-oriented (no grammar needed); sitemap.xml via stdlib xml.etree. Fixture per rule id.
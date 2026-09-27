---
id: T-6610
title: 'SEO119/SEO120: split scaled-content vs. doorway-page detectors'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
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
- src/frob/webapp/_seo_spam.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-5365: SEO116 implements one combined heuristic (route-generation call + large quoted-string array) covering both the scaled-content and doorway-page halves of the ticket body's single corpus item, leaving SEO119/SEO120 (2 of the reserved SEO113-120 8-id block) unused. Design and implement two distinct detectors: scaled-content (templated pages with near-duplicate body content) and doorway-page (multiple landing pages targeting near-identical search queries with only a location/keyword swap).
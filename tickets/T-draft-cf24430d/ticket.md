---
id: T-draft-cf24430d
title: 'SEO101-112: per-page tags'
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: high
parent: T-5147
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_seo_tags.py
- tests/fixtures/webapp/seo1xx/**
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
Unique title/meta-description per route, og:title/og:type/og:image/og:url, canonical link, favicon, JSON-LD LocalBusiness required properties. html-lang cross-refs A11Y104's rule id, not duplicated. Fixture per rule id via 5147-1.
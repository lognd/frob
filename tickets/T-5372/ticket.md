---
id: T-5372
title: 'COMPLY101-108: privacy-policy page content, CCPA/CalOPPA'
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: high
parent: T-5145
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
- src/frob/webapp/_comply_privacy.py
- tests/fixtures/webapp/comply1xx/**
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
Required /privacy page + text-search for 'categories collected'/'effective date'/'do not track' sections (CalOPPA 22575(b)), 12-month-staleness lint on a frontmatter last_updated date (CCPA 1798.130(a)(5)), Do-Not-Sell link presence when a tracking pixel is detected (CCPA 1798.135(a)). Markdown/HTML content lint (regex/text-search, no grammar needed). Fixture: compliant and non-compliant privacy-policy pages.
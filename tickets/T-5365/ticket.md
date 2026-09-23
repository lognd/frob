---
id: T-5365
title: 'SEO113-120: spam-policy shape detectors'
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
- src/frob/webapp/_seo_spam.py
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
Keyword stuffing (shape-based n-gram repetition, NOT a density threshold per the story's explicit correction), cloaking via user-agent branching, hidden text via CSS (color==background/font-size:0/opacity:0/off-screen-position -- needs CSS grammar, WEBSUB-1b), scaled-content/doorway-page config advisories, framework-default-title detection (Vite/CRA/Next), staging-without-noindex. Fixture per rule id.
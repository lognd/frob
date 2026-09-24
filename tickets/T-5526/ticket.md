---
id: T-5526
title: 'fixture secret shapes: a gate that refuses committed test fixtures whose secret-looking
  strings match push-protection detector patterns; canonical placeholder table'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.535.0
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
found while fixing T-5658 (WEBSEC316's own fixture matched a real Stripe live-key shape and got blocked by GitHub push protection on dev, commit 8ff633a0): today avoiding this is a convention (know the detector patterns, pick a placeholder that dodges them), not an enforced rule, so it will recur across every WEBSEC/SEO/COMPLY fixture family that plants a secret-shaped positive control. Add a frob gate that scans committed fixture files (and generally any tracked file) for strings matching known push-protection detector patterns (GitHub's own published secret-scanning patterns: Stripe, AWS, GitHub tokens, etc.) and refuses the commit/check, plus a canonical placeholder table (e.g. frob.webapp secret-fixture helpers) every WEBSEC/COMPLY/SEO fixture author should reuse instead of hand-rolling a placeholder.
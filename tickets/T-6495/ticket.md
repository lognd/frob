---
id: T-6495
title: admission and rate limiting (SYSDESIGN201+)
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-6476
tier: story
sprint: sysdesign
runs_last: false
milestone: 0.539.0
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
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: admission and rate limiting (SYSDESIGN201+)
kind: feature
tier: story
parent: T-SYS-EPIC
milestone: 0.539.0
sprint: sysdesign
scope: (none -- story, no direct code scope)
blocked_by: []

Body:

The declared-vs-observed check for strata `boundary admit { rate_limit; max_size; }` is
RULE-ONLY (the grammar already ships, per T-0069 -- STRATA-EXPRESSIVENESS.md's correction to
the prior inventory). This story links to the reserved WEBSEC rate-limit ids
(WEBSEC10x/20x, reserved by T-5301 for the T-5140 epic, all "(not yet implemented)" per
gates.md) rather than duplicating that reservation -- SYSDESIGN201 checks the DESIGN-MODEL
declaration/proof pairing, WEBSEC's still-unshipped ids would check the deployed HTTP surface;
these are two different layers of the same concern and must stay two different rule ids per
the NO DUPLICATION principle (matching the CDN/TLS boundary already drawn at research row
10.1/10.3).

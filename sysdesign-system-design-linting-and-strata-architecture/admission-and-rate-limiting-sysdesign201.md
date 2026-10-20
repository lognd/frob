+++
id = "01M3AXSDAZX9B4327J18H8GE7S"
title = "admission and rate limiting (SYSDESIGN201+)"
type = "story"
category = "todo"
priority = "low"
parent = "01M3AXSDACKS00T3E853M1J0DR"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:26Z"
aliases = ["T-6495"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
+++

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

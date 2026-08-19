---
id: T-2590
title: Recovered from T-2561's phantom TICK006 citation of T-draft-5e5a0e2b
state: dropped
kind: bug
origin: agent
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2561's Done report claimed T-draft-5e5a0e2b was filed, but T-draft-5e5a0e2b resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> live lease
(T-2377) throughout this session, so widening T-2561's scope onto it
would have been a lease collision, not a legitimate expansion. Filed
T-draft-5e5a0e2b (`docs/modules/gates.md` scope) to add TICK012 (and the
pre-existing CYCLE001 gap found alongside it) once that lease frees up.
DOCEN

## Drop reason
- 2026-08-19: Draft T-draft-5e5a0e2b's intended work (add TICK012, and the CYCLE001 entry alongside it, to docs/modules/gates.md's DOCENUM001 rule-catalog enumeration) is already complete on current main -- both TICK012 and CYCLE001 already appear in the frob:enumerates directive (line 13) and have table rows (lines 31, 55). Measured: 'uv run frob check --only gates --json' on current main tip reports zero DOCENUM001 findings for docs/modules/gates.md (only pre-existing DOC008/NEGEXIST001 findings, unrelated). The draft itself (commit 45f65b4fa on the T-2561 worktree branch) never merged into main (git merge-base --is-ancestor 45f65b4fa main -> false), so the TICK006 citation is phantom, but the work it described was independently completed by later edits to gates.md, not lost.

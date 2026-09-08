---
id: T-4346
title: Audit remaining T-3844-promoted rule families for waivability/structural silence
  (PERF/SEC/PII/ARCH/DOC/REG/COMPLIANCE/KRB/DEPLOY/FFI/LANG/NATIVE/PROFILE/WAIVE/VET/REL/etc.)
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob.toml
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
T-4340 checked the two known failure shapes (TICK005/COV002's stale-git-object-path structural silence; SCOPE002/TICK009's unwaivable-synthetic-finding shape) across every gates/*.py and strata/*.py Violation-construction site it could reach in the time budgeted, and additionally spot-checked BUG002/BUG003/REL001/TICK014 (which also emit file="tickets.md", line=0 synthetic Violations) -- none of those are the SCOPE002/TICK009 shape because their remedy is satisfying a real, currently-measurable requirement (repro-evidence pass/fail state, an open-ticket milestone gate), not a frob:waive escape hatch for an inherently-heuristic advisory, so they were left at error. COV002 was re-verified to already carry the T-1582 v1/v2 dispatch fix and is not TICK005-shaped. That leaves roughly 270 of the ~280 T-3844-promoted rules (everything outside the tickets/milestone/bug-repro cluster T-4328/T-4331/T-4340 already walked) NOT individually re-derived against property 2 (waivability) and property 3 (structural silence) with the same per-rule rigor -- PERF001-014, SEC*, PII*, ARCH*, DOC*, REG001-007/012, COMPLIANCE*, KRB*, DEPLOY*, FFI*, LANG*, NATIVE*, PROFILE001, WAIVE001-011 (non-cluster), VET*, REL200-397, SYS001-205 (non-SYS101/107), DEC000-003, DEBT001-003, CROSSTICKET001, CVEFP001, DUP001-003, WIRE001-003, FUZZ001-003, THREAT001-006, TODO001-003, and the rest of the frob.toml [gates.severity] T-3844 block. Method (per T-4331's Done report): for each rule, find every rule=<ID> Violation-construction site, check whether the emitted Violation carries a real anchorable file:line/symref (property 2 -- watch for hardcoded line=0 against a path a migration removed), and check the containing function/module for a stale git-object read, a removed file path, or a config/feature-flag gate that would make it silently unreachable in this repo's current state (property 3, the TICK005/COV002-T-1582 shape). Do NOT mass-demote -- most are plausibly fine; report per-rule reasoning for anything left at error, and for anything demoted or newly reachable, ask whether the current tree actually violates it now that it can fire.
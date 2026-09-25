---
id: T-6433
title: 'SYSDESIGN201: trust-escalating boundary with no `admit.rate_limit`/`admit.max_size`
  declared'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-6495
tier: ticket
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
scope:
- src/frob/strata/_boundary_admission.py (new)
- tests/fixtures/sysdesign/sysdesign201/**
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'DOC006 inline waivers: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 2924
  new_length: 3102
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN201: trust-escalating boundary with no admit.rate_limit/admit.max_size declared
kind: feature
tier: leaf
parent: T-SYS-SD
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/strata/_boundary_admission.py (new), docs/modules/gates.md (SYSDESIGN201 row),
       tests/fixtures/sysdesign/sysdesign201/**
blocked_by: []
tag: Static: design (declared-vs-observed, REL2xx-shaped pair)

Finding (STRATA-EXPRESSIVENESS.md, section D, "WAF / rate limiter / quota / request size
limits" -- CORRECTING THE PRIOR INVENTORY): "Direct read of grammar_flow.rs's
`parse_phase_block` (the `boundary ID endorse|declassify FLOW : L -> L { admit { rate_limit
QUANTITY; max_size QUANTITY; } ... }` six-phase construct) shows `admit.rate_limit` and
`admit.max_size` ARE real, shipped grammar tokens (docs/strata/boundary.md's 'six phases'
model, T-0069)... So: rate limiting and request-size limits are EXPRESSIBLE in the surface
grammar (boundary admit phase); WHETHER any rule currently CHECKS for a missing admit/
rate_limit clause the way REL200/210/etc check for missing timeout/health is a separate, still-
open question -- grep... found none... EXPRESSIBLE grammar, NOT YET LINTED (RULE-ONLY gap, not
a grammar gap). Proposal (RULE-ONLY): new REL-family rule 'a boundary crossing an
untrusted->trusted trust escalation with no `admit.rate_limit` declared' (REL2xx-sibling,
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->module frob.strata._boundary_admission). Authority: OWASP API Security Top 10 (API4:2023
Unrestricted Resource Consumption)."

Research row 3.4 (same authority): OWASP API Security Top 10 (2023), https://owasp.org/
API-Security/editions/2023/en/0x11-t10/ -- "API4:2023 - Unrestricted Resource Consumption:
Satisfying API requests requires resources such as network bandwidth, CPU, memory, and
storage... Successful attacks can lead to Denial of Service or an increase of operational
costs."

<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->Acceptance criteria: new module `frob.strata._boundary_admission` implements the declared/
proven pair as ONE rule id, per the coordinator's contiguous-numbering directive: SYSDESIGN201
fires on either of two conditions -- a boundary crossing untrusted->trusted with no
`admit.rate_limit`/`admit.max_size` declared flags as missing; a boundary declaring
`admit.rate_limit`/`admit.max_size` but with no bound code containing a real rate-limiter/
body-size-cap token flags as unproven -- same two-step discipline REL220/221 uses, folded
into one id here. gates.md gets the single SYSDESIGN201 row, cross-referencing WEBSEC10x/20x
as the separate, still-unshipped deployed-surface layer rather than re-describing it. Positive-control fixture: tests/fixtures/sysdesign/sysdesign201/
trust-escalation-no-admit/**.

---
id: T-4281
title: land proof does not distinguish an infra-failure unmeasured verification from
  a genuine skip
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_verify.py
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_land_verify_claims_outcome.py
- tests/test_ticket_land_proof_claims.py
- tests/unit/test_ticket_runner_gate_findings.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_verify.py
  reason: 'T-4281: the actual check-spawn (_verify.py) and LAND-PROOF printer (_land_cmd.py)
    live outside the ticket''s original two-file scope; the fix requires naming the
    infra-failure cause at its source and printing it'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'T-4281: the actual check-spawn (_verify.py) and LAND-PROOF printer (_land_cmd.py)
    live outside the ticket''s original two-file scope; the fix requires naming the
    infra-failure cause at its source and printing it'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_land_verify_claims_outcome.py
  reason: 'T-4281: new tests reproducing/pinning the INFRA_UNMEASURED classification
    and its LAND-PROOF printing live in these existing test files'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_ticket_land_proof_claims.py
  reason: 'T-4281: new tests reproducing/pinning the INFRA_UNMEASURED classification
    and its LAND-PROOF printing live in these existing test files'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_ticket_runner_gate_findings.py
  reason: 'T-4281: new tests reproducing/pinning the INFRA_UNMEASURED classification
    and its LAND-PROOF printing live in these existing test files'
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
acceptance:
- text: given a land whose graph build failed to take the cache lock (or otherwise
    hit an infrastructure error) during re-verification, when the land emits its LAND-PROOF
    line, then the reported state is distinguishable from a land that was DELIBERATELY
    not re-verified (e.g. a deferred/rapid-profile skip)
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-4258 (serve daemon graph-cache lock starvation). T-4258's own acceptance criterion 3 required this, but the fix lives entirely in src/frob/tickets/_land_verify.py and src/frob/tickets/_land.py's SKIPPED_UNMEASURED handling -- outside T-4258's src/frob/serve/_daemon.py + src/frob/serve/_warm.py scope, and a large enough subsystem (land-proof semantics) to deserve its own ticket rather than widen T-4258's blast radius. Context: SKIPPED_UNMEASURED already exists as one outcome in src/frob/tickets/_land_verify.py (~line 54) and is used both for a genuinely-deferred check (rapid profile, T-1575/T-1684) and would ALSO be the outcome of a graph build that failed because it lost a cache lock race -- today's LAND-PROOF line prints the same 'SKIPPED-UNMEASURED' string for both, which is exactly the silent-zero shape T-4258's own body describes ('an absent measurement presented as an uneventful one'). Needs a real reason code or sub-classification threaded through, not just a cosmetic label change.
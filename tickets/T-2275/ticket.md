---
id: T-2275
title: 'LAND-PROOF: wire _LAST_ORPHAN_EVIDENCE_OUTCOME into _print_land_proof (T-2091
  parity for the T-2255 orphan-evidence check)'
state: queued
kind: feature
origin: agent
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'LAND-PROOF: line gains orphan_evidence_check= printed from _LAST_ORPHAN_EVIDENCE_OUTCOME'
  evidence: []
- text: No change to the returned verified bool -- surfacing only
  evidence: []
- text: Test mirrors test_ticket_land_proof_claims.py's SKIPPED_UNMEASURED-not-printed-as-verified-True
    coverage
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2255 gave `_check_orphaned_evidence_deletion` a process-local
`_OrphanEvidenceCheckOutcome` record (`_LAST_ORPHAN_EVIDENCE_OUTCOME` in
`src/frob/tickets/_land.py`, the exact T-2091 pattern already used for
the claims-reverify check) plus a WARNING-level log line for the
SKIPPED_UNMEASURED case. That satisfies T-2255's acceptance criterion 5
(ran vs skipped is distinguishable after the fact) via the land's own
console output, but stops short of T-2091's full treatment: T-2091 wired
`_ClaimsReverifyOutcome` into `_print_land_proof`
(`src/frob/app/ticket_runner/_land_cmd.py`) so the `LAND-PROOF:` line
itself names the outcome as its own `claims_reverify=` field.

T-2255 was scoped to `src/frob/tickets/_land.py` alone (not paired with
`_land_cmd.py` the way T-2091 was), so this ticket does the identical
wiring for `_LAST_ORPHAN_EVIDENCE_OUTCOME`: `_print_land_proof` pops it
by `report.ticket_id` and prints it as its own
`orphan_evidence_check=` field on the `LAND-PROOF:` line, mirroring
`claims_reverify=` exactly.

## Acceptance
- `LAND-PROOF:` gains an `orphan_evidence_check=` field printed from
  `_LAST_ORPHAN_EVIDENCE_OUTCOME`, `unknown` when no entry exists (dry
  run / recovered marker, matching `claims_reverify=`'s own fallback).
- No behavior change to the returned `verified` bool -- this is
  surfacing only, exactly as T-2091 was for its own check.
- A test mirroring `tests/test_ticket_land_proof_claims.py`'s coverage
  of the SKIPPED_UNMEASURED-not-printed-as-verified-True shape.

---
id: T-2877
title: 'SELFAUDIT001: T-2849''s process/_reap.py env.read growth and a new via-less
  core ffi grant lack ratchet/because coverage'
state: in-progress
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
evidence_scope:
- tests/unit/strata/test_effects.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 needs this directive: no code behavior change, only strata/ratchet
    declaration corrections'
  actor: logan
  at: '2026-08-22'
  old_length: 1944
  new_length: 2287
evidence:
- tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_deleting_lock_entry_does_not_bypass_the_ratchet
- tests/unit/strata/test_effects.py::TestCapabilityRatchet::test_unscoped_grant_is_never_ratcheted
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

Measured while working T-2871 (unrelated ticket): unbudgeted frob check
--json (gate-summary present) shows 3 SELFAUDIT001 errors on the core
node, not caused by T-2871's scope (T-2851/T-2843 gates splits), left
out of that ticket deliberately to stay narrow:

1. SYS111: core::env.read via-list grew to 4 sites, above the committed
   ratchet ceiling of 3. The new site is src/frob/process/_reap.py,
   added by T-2849 (frob check forkserver leak fix, landed as
   5dad1ad96) -- an already-declared via-source for core, not a fresh
   capability. Needs a ratchet bump (accepted_count 3->4) with a reason
   citing T-2849.

2. SYS107 + SYS112: a via-less (ambient) may "ffi" grant on the core
   node with no // because: "..." justification comment, and the core
   node binds 126 files (> 20), so the via-less grant is flagged as
   too wide to leave unnarrowed. Needs either a because justification
   comment (if the capability is genuinely used from anywhere in the
   node, matching the existing pattern used elsewhere for ambient
   grants) or a via-list naming the actual ffi call site(s), whichever
   the measurement supports -- determine which before writing anything.

## Plan

- git blame/log design/frob.strata to find which land introduced the
  via-less may "ffi" grant on core and why.
- If ffi is called from a small, identifiable set of files: convert to
  a via-list naming them (narrowest fix).
- If it is genuinely called from wherever in the package (matching the
  ambient-grant pattern already used for other node/capability pairs in
  this file): add a because comment stating why, following the
  existing style.
- Bump core::env.read ratchet ceiling 3->4 in
  docs/design/registry/capability-via-ratchet.lock.json citing T-2849.
- Re-measure SELFAUDIT001 for the core node to zero before landing.
- Never widen a grant beyond what the measurement shows is genuinely
  used.

## Failure log

(none yet)

frob:no-behavior-change reason="T-2877 is a static declarative fix (design/frob.strata via-scoping and docs/design/registry/capability-via-ratchet.lock.json ratchet ceilings) correcting T-2849's capability declarations to match its own code -- no runtime behavior changes, only which files a may-grant names/how large a committed ceiling is"
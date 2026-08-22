---
id: T-2871
title: 'Fix SELFAUDIT001: T-2851/T-2843 splits left gates capability via-lists stale,
  plus 2 ratchet ceiling bumps'
state: done
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
  old_length: 3103
  new_length: 3460
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

Unbudgeted frob check --json (gate-summary present) shows 13 SELFAUDIT001
errors (plus 2 SELFAUDIT001 warnings not in scope here, and unrelated
COV003/PERF004/CLAUDE001/TICK004 findings out of scope).

Grouped by root cause:

1. (5 errors) T-2851 split BUG002/must-still-pass repro-classification
   code from src/frob/gates/_mutation_evidence.py into a new
   src/frob/gates/_bug_repro.py. The gates node's may "fs.write",
   may "exec", and may "env" via-lists in design/frob.strata still
   name only _mutation_evidence.py; the fs.write/exec/env.read call
   sites moved to _bug_repro.py and now read as undeclared capabilities
   at that file's line numbers (428, 525, 546, 562, 590).

2. (1 error) SYS101: gates' may "exec" via "_mutation_evidence.py" is
   now a stale declaration -- the exec calls that justified it moved to
   _bug_repro.py in the same T-2851 split, so the via-source is never
   observed anymore. Same root cause as group 1: the via-list needs
   _mutation_evidence.py replaced with _bug_repro.py for the exec grant.

3. (5 errors) T-2843 split docstatus/docmake/docseverity gates out of
   src/frob/gates/_doclink_docanchor.py into (among others) a new
   src/frob/gates/_docstatus.py. The gates node's may "fs.read"
   via-list still names only _doclink_docanchor.py; _docstatus.py's
   fs.read calls (lines 158, 201, 290, 366, 498) read as undeclared.

4. (2 errors) SYS111 ratchet ceiling: cli::fs.read grew from the
   committed ceiling of 18 to a measured 19 sites (the new site is
   src/frob/app/_check_chunking_baseline.py, itself an existing,
   already-declared via-source added by a prior split, not a fresh
   capability); testsuite::env.read grew from ceiling 7 to measured 8
   (the new site is tests/unit/test_check.py, likewise an existing test
   file with a legitimate env.read call). Same pre-existing accumulated
   growth shape T-2743 already established a precedent for: bump
   accepted_count in docs/design/registry/capability-via-ratchet.lock.json
   with a reason citing this ticket, rather than re-justifying each site.

## Plan

- Add src/frob/gates/_bug_repro.py to the gates node's fs.write and env
  via-lists in design/frob.strata (narrowest fix: via-list repoint, no
  new capability, no widened grant).
- Replace src/frob/gates/_mutation_evidence.py with
  src/frob/gates/_bug_repro.py in the gates node's exec via-list (the
  call moved, not multiplied).
- Add src/frob/gates/_docstatus.py to the gates node's fs.read via-list.
- Bump cli::fs.read accepted_count 18->19 and testsuite::env.read
  accepted_count 7->8 in capability-via-ratchet.lock.json, each with a
  reason citing the already-declared-via-source measurement above.
- Do NOT touch COV003 (another agent's ticket), and do not widen any
  capability grant beyond what is already declared for the node --
  every fix here is a via-list correction or a ratchet-ceiling bump for
  an already-declared source, never a new may grant.
- Re-measure SELFAUDIT001 to zero (unbudgeted frob check --json,
  gate-summary present) before landing.

## Failure log

(none yet)

frob:no-behavior-change reason="T-2871 is a static declarative fix (design/frob.strata via-lists and docs/design/registry/capability-via-ratchet.lock.json ratchet ceilings) correcting capability declarations to match code that T-2851/T-2843 already moved -- no runtime behavior changes, only which files a may-grant names/how large a committed ceiling is"
---
id: T-2405
title: widen PORT001 scan scope past src/frob/gates/ (repo-wide src/frob/ hardcoded-identity
  sweep)
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_port_selfcheck.py
- tests/unit/gates/test_port_selfcheck.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/gates/test_port_selfcheck.py::TestPort001::test_strata_and_vet_are_scanned_since_t2405
- tests/unit/gates/test_port_selfcheck.py::TestPort001::test_non_detector_package_code_never_scanned
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 5c70af4bfb50bd0caf9ddc2eb08c4c3b7c466f4b
---
Child of T-2384/T-2388. PORT001 (T-2388) deliberately scans src/frob/gates/
only -- do not widen inside T-2388 itself, per coordinator instruction
(2026-08-18). This ticket is that widening.

Starting set (coordinator's own broader grep, git grep -ln '"src/frob/'
-- opening quote + src/frob/ + any continuation, repo-wide minus gates/):

  src/frob/tickets/_models.py                      (OVER_BROAD_LITERAL_GLOBS)
  src/frob/tickets/_land_merge_zones.py
  src/frob/tickets/_new_gate_rule_acceptance.py
  src/frob/app/ticket_runner/_land_cmd.py
  src/frob/app/ticket_runner/_new.py
  src/frob/refactor/_repointer.py
  src/frob/strata/_packs.py
  src/frob/strata/_selfconform.py

Re-run PORT001's own detector (or an extended-scope variant of it) against
these 8 first -- do not assume every hit is real without AST verification,
the SAME calibration discipline T-2388 already demonstrated (43 raw
substring hits narrowed to 5 true positives). Widening _tracked_gate_files
past src/frob/gates/** likely also needs _walk_lint.py::
tracked_python_files_for_gate retargeted (it hardcodes `git ls-files --
src/frob`, the T-2389 sibling noted in T-2388's Done report) since that
shared helper is what PORT001/WALK001/RENDER001 all reuse to enumerate
tracked files at all.

Preserve PORT001-PATH vs PORT001-IDENT's severity/promotion split (T-2388):
PATH is the promotion-bar (WARN->ERROR) rule, IDENT stays advisory-only,
never individually waiver-required. Print the scanned scope alongside the
count on every run, same discipline as the gates/-only version.
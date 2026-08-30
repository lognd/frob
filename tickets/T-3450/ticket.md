---
id: T-3450
title: 'SYS100 undeclared capability: tests/unit/test_check_admission.py exec sites
  missing from testsuite via-list'
state: done
kind: bug
origin: agent
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
- tests/unit/test_check_admission.py
- tests/system/test_frob_self_model.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: collides with in-progress T-3447's lease on the same file; T-3450's own
    fix (declaring the missing exec via-site) may trip a downstream SYS111 ratchet
    bump, but that is handled by the land pipeline's own fix_sys111_capability_ratchet_sync
    Tier-A auto-fix, not a manual edit this ticket needs to make itself
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/system/test_frob_self_model.py
  reason: adding a narrow, non-maskable SYS100 regression test for tests/unit/test_check_admission.py's
    exec sites, following the exact test_fragments_module_fs_read_is_declared_not_selfaudit001
    precedent already in this file
  actor: logan
  at: '2026-08-29'
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_check_admission_exec_sites_are_declared_not_selfaudit001
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED locally while working T-3447 (SYS111 ratchet ticket, 2026-08-30):
after fixing all 5 SYS111 capability-ratchet breaches, tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations still fails with 10 SELFAUDIT001 violations of a DIFFERENT family (SYS100, not SYS111):

  SELFAUDIT001: self-audit family SYS100 node=testsuite: capability 'exec' observed at tests/unit/test_check_admission.py:373 but not declared
  (and 9 more, same file, lines 374/375/377/378/406/412/435/441/500)

tests/unit/test_check_admission.py calls exec-capability code (subprocess/os.system-shaped calls, per frob.vet's capability scan) that design/frob.strata's testsuite node's exec via-list does not enumerate. The file is already referenced once elsewhere in design/frob.strata (from T-3287/T-3256, which landed this file originally) but not for the exec capability specifically -- this is a genuinely undeclared capability site, not a SYS111 ratchet growth issue, and out of T-3447's scope (which is specifically the SYS111 capability-ratchet lock).

FIX: add tests/unit/test_check_admission.py to design/frob.strata's testsuite exec via-list (see the existing `may "exec" via [...]` grant testsuite already declares, ~line matching other testsuite exec via-list members), verified by re-running the SYS100 self-audit (this same test, or `frob check --only sys`). This is a SYS100 fix (declare the site), not a SYS111 fix (bump a ceiling) -- do not conflate the two; SYS111's own ratchet ceiling for testsuite::exec may also need bumping by 1 afterward if declaring this via-list addition increases the counted site total past the current ceiling (already bumped to 225 by T-3447 for a different, coincidental reason -- re-measure after this fix, don't assume the same number covers both).

Filed while working T-3447 (out of scope for that ticket -- T-3447's scope is the SYS111 ratchet, not SYS100 undeclared-capability findings).
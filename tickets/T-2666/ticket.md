---
id: T-2666
title: testsuite node's ambient exec grant (T-2503) collides with SYS107 fail-closed
  policy (T-2224)
state: done
kind: bug
origin: human
created: '2026-08-19'
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
- tests/unit/strata/test_sys107_via_scope_advisory.py
- tickets/T-2676/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: SYS111 ratchet gate ties directly to the exec via-list this ticket restores
    on testsuite; the count changed from 188 (T-2488, pre-T-2503) to 194 (fresh T-2666
    scan), so the ratchet ceiling must move in the same diff or SYS111 refuses the
    land
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: SYS111 ratchet gate ties directly to the exec via-list this ticket restores
    on testsuite; the count changed from 188 (T-2488, pre-T-2503) to 194 (fresh T-2666
    scan), so the ratchet ceiling must move in the same diff or SYS111 refuses the
    land
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/unit/strata/test_sys107_via_scope_advisory.py
  reason: the three tests named in this ticket's own evidence list cannot serve as
    passing evidence -- they also fail on testsuite's fs.read/fs.write ambient grants,
    an adjacent pre-existing defect this ticket was explicitly told NOT to fix (filed
    as a follow-up). A narrower regression test isolating just the exec/SYS107 collision
    this ticket actually fixes is needed as real evidence
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tickets/T-2676/**
  reason: the new-ticket auto-commit for T-2676 (filed from this ticket
    for the fs.read/fs.write follow-up) lands its own ticket dir on this branch; SCOPE001
    flags it otherwise
  actor: logan
  at: '2026-08-19'
evidence:
- tests/unit/strata/test_sys107_via_scope_advisory.py::TestTestsuiteExecViaListRestored::test_testsuite_exec_has_no_via_less_sys107_finding
designated_repro_test: tests/unit/strata/test_sys107_via_scope_advisory.py::TestTestsuiteExecViaListRestored::test_testsuite_exec_has_no_via_less_sys107_finding
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2634 fixed 3 of the 6 originally-listed red tests (test_threat.py's
DEFAULT_BENIGN_CAPABILITIES count, test_mutation_audit.py's
test_every_may_is_load_bearing, and test_second_detector_gaps... after
also folding in a pre-existing net.connect gap found during that
investigation). The remaining 3 --
tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant,
tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean,
tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
-- share ONE root cause, confirmed by direct investigation, distinct from
the other three and materially larger to fix:

T-2503 (landed 2026-08-18) converted `testsuite` node's `exec`/
`fs.read`/`fs.write` `may` declarations from enumerated per-file `via`
lists (~676 combined file entries) to ambient, via-less whole-node
grants, explicitly reasoning that "every file under this node's tests/**
code binding legitimately exercises all three" and that per-file
enumeration "only produced merge-conflict churn, not a decision."

T-2224 (landed 2026-08-16, TWO DAYS BEFORE T-2503) had already made
`exec`/`eval`/`install-hook`/`ffi` (`SYS107_FAIL_CLOSED_ATOMS`)
ALWAYS Severity.ERROR at the SYS107 (via-less-may-on-a-large-node)
gate when declared via-less on a node exceeding the file-count
threshold (20 files; testsuite currently binds 601), regardless of
`[strata] require_may_scope`. T-2503's ambient `exec` grant on
testsuite collides directly with this: `frob check --only sys` on
unmodified main (measured directly, this investigation) reports a real
ERROR-severity SELFAUDIT001/SYS107 finding for testsuite's via-less
`exec` grant. The `fs.read`/`fs.write` via-less grants stay WARN-only
(not fail-closed) and are not part of this gap -- they were a
deliberate, disclosed T-2503 decision and should NOT be reverted.

This is a live, uncaught regression from T-2503's own land (should have
been caught by `frob check --only sys` at land time but evidently
wasn't, or was overridden) -- not something T-2634's fixture-repair
scope can absorb. The fix requires either:
  (a) restoring `exec`'s via-list to enumerated form (a large diff --
      the pre-T-2503 list had ~145 files; new exec-using test files
      have been added since and would need to be identified fresh, not
      copied stale from git history), or
  (b) a design-level decision to exempt this specific node/atom
      combination from SYS107's fail-closed policy (T-2224), which
      would need to be a deliberate, documented carve-out, not a
      mechanical waiver.

Either way this is materially larger than a one-line stale-count fix
(the shape of the other three fixes in T-2634) and touches gate policy,
not just test fixtures -- filed separately per T-2634's own dispatch
guidance ("if the six turn out to need materially different fixes and
one is much larger, land what is coherent and file the remainder").

Do NOT weaken SYS107's fail-closed policy (T-2224) to make this
convenient -- narrow the grant or make an explicit, justified design
decision.

Evidence to re-verify after a fix:
  tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
  tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean
  tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
  frob check --only sys (SELFAUDIT001/SYS107 for node=testsuite, capability=exec, should report 0 errors)
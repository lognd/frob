---
id: T-2930
title: Triage macOS-only pytest failures found via T-2917 CI matrix (156 failures,
  non-fcntl/prctl remainder)
state: in-progress
kind: bug
origin: human
created: '2026-08-25'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_process_reap.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'triage/investigation ticket: enumerate and classify 156
  macOS-only pytest failures before deciding which files to touch'
scope_changes:
- op: remove
  glob: tests/
  reason: triage-only ticket, no fixed file set yet
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/unit/test_process_reap.py
  reason: 'T-2930: fix macOS-CI test-only fragility in PDEATHSIG self-kill tests missing
    a sys.platform pin'
  actor: logan
  at: '2026-08-26'
body_changes:
- mode: append
  reason: 'T-2930: land refused BUG002 (confirmatory-only) since this ticket''s actual
    fix is test-only with no production behavior change'
  actor: logan
  at: '2026-08-26'
  old_length: 2157
  new_length: 2992
- mode: append
  reason: 'T-2930: add frob:no-behavior-change directive so BUG002 checks the correct
    direction for this test-only fix'
  actor: logan
  at: '2026-08-26'
  old_length: 2991
  new_length: 3298
evidence:
- tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_self_kills_on_missed_reparent_race
- tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_self_kills_when_already_reparented_before_entry
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured while running T-2917 (CI matrix add): the macos-latest build job
(GitHub Actions PR #1, run 32920399634, job 98032723003) produced 156
FAILED pytest node ids on a real macOS runner. Some are directly the
known POSIX/Linux-only primitives T-2918/T-2919 target (fcntl advisory
locks, ctypes libc prctl in arm_parent_death_signal) and will be
resolved by that series.

This ticket is for the REMAINDER: failures visible in the same run that
are not fcntl/prctl-shaped, e.g.:
  - tests/unit/strata/test_export_golden.py::TestExportGolden (test_seccomp,
    test_k8s, test_iam) -- string-equality goldens that may be line-ending
    or JSON-key-order sensitive on macOS
  - tests/unit/test_gitattributes_merge.py::TestAttachmentCrlfSuppression::test_unrelated_text_file_still_gets_autocrlf_conversion
  - tests/unit/perf/test_serial_pools.py::TestInstallSerialPools::test_without_serial_pools_worker_is_unattributed
    -- a hardcoded timing threshold (0.05s) that a slower/more
    contended macOS CI runner can miss
  - tests/unit/strata/test_sys003_calibration.py::TestSys003ZeroOnFrobsOwnRepo::test_sys003_zero_against_live_repo_design
    -- flags a real SYS003 finding at src/frob/tickets/_land.py:440;
    needs triage for whether this is a genuine, pre-existing
    architecture violation only now surfaced because a differently-
    ordered/cached run reached it, or an environment artifact
  - a broad cluster of ticket-lease/worktree/land-guard tests
    (test_ticket_leases.py, test_ticket_work_and_land_finish.py,
    test_worktree_guard.py, test_land_finish_guard.py,
    test_daemon_proxy_lease_t1276.py, test_coordinator_scripts.py) whose
    failure modes need triage to separate "assumes Linux process
    semantics, in scope for a PLATFORM001-style fix" from "assumes a
    Linux-only fixture/helper not related to fcntl/prctl at all"

Full raw list is in the run's log (gh api repos/lognd/frob/actions/jobs/98032723003/logs);
grep for "^2026.*FAILED " to reproduce the 156-line list. Triage into
either PLATFORM001-fixable (T-2919's own gate should then catch the
primitive) or genuine macOS-only test bugs, and file/fix accordingly.

T-2930's own fix is test-only: tests/unit/test_process_reap.py's two
PDEATHSIG self-kill tests were missing a sys.platform pin, so they
short-circuited on any non-Linux runner before reaching their mocked
machinery. The fix adds monkeypatch.setattr(sys, "platform", "linux")
to both tests -- no production code in src/frob/process/_reap.py
changed at all. There is no behavior for a mutation-kill test to prove
here: the "defect" was entirely in the test's own setup, not in
arm_parent_death_signal's real logic, which was already correct and
already covered (test_arms_successfully_on_linux,
test_returns_false_off_linux). BUG002's confirmatory-only concern
(evidence that passes at both parent and fix, proving nothing) does
not apply in the usual sense since there is no diff-touched production
code for a mutant to touch at all.

frob:no-behavior-change reason="T-2930's fix touches only tests/unit/test_process_reap.py (a sys.platform pin on two mocked tests); no production code in src/frob/process/_reap.py changed, so the designated evidence must PASS at the parent commit too -- there is no behavior change for a mutant to kill."
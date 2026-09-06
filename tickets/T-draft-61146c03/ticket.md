---
id: T-draft-61146c03
title: 'Windows CI: fix suite-abort hang plus 3 mandatory-lock/CRLF Windows failures
  (subset of T-3936)'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_conftest_suite_result_status.py
- tests/ticket_land_suite/test_land_lock.py
- tests/test_tickets_mutation_evidence.py
- tickets/T-draft-fe768f82/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets/T-draft-fe768f82/ticket.md
  reason: 'close scope-closure gaps flagged by frob check: the filed draft ticket
    file itself, plus production/test modules that touched-test-files'' pre-existing
    frob:tests bindings and private-helper fakes reach into'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'close scope-closure gaps flagged by frob check: the filed draft ticket
    file itself, plus production/test modules that touched-test-files'' pre-existing
    frob:tests bindings and private-helper fakes reach into'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/tickets/_mutation_evidence.py
  reason: 'close scope-closure gaps flagged by frob check: the filed draft ticket
    file itself, plus production/test modules that touched-test-files'' pre-existing
    frob:tests bindings and private-helper fakes reach into'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/conftest.py
  reason: 'close scope-closure gaps flagged by frob check: the filed draft ticket
    file itself, plus production/test modules that touched-test-files'' pre-existing
    frob:tests bindings and private-helper fakes reach into'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_conftest_console_ctrl_guard.py
  reason: 'close scope-closure gaps flagged by frob check: the filed draft ticket
    file itself, plus production/test modules that touched-test-files'' pre-existing
    frob:tests bindings and private-helper fakes reach into'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_process_guard.py
  reason: 'close scope-closure gaps flagged by frob check: the filed draft ticket
    file itself, plus production/test modules that touched-test-files'' pre-existing
    frob:tests bindings and private-helper fakes reach into'
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_process_pid_liveness.py
  reason: 'close scope-closure gaps flagged by frob check: the filed draft ticket
    file itself, plus production/test modules that touched-test-files'' pre-existing
    frob:tests bindings and private-helper fakes reach into'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: src/frob/tickets/_land.py
  reason: 'revert: these pulled in a huge cascading doc scope closure via unrelated
    pre-existing frob:tests/doc bindings in src/frob/tickets/_land.py; this ticket
    touches only test files, keep scope narrow and handle SCOPE002 via targeted waivers
    instead'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: src/frob/tickets/_mutation_evidence.py
  reason: 'revert: these pulled in a huge cascading doc scope closure via unrelated
    pre-existing frob:tests/doc bindings in src/frob/tickets/_land.py; this ticket
    touches only test files, keep scope narrow and handle SCOPE002 via targeted waivers
    instead'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: tests/conftest.py
  reason: 'revert: these pulled in a huge cascading doc scope closure via unrelated
    pre-existing frob:tests/doc bindings in src/frob/tickets/_land.py; this ticket
    touches only test files, keep scope narrow and handle SCOPE002 via targeted waivers
    instead'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: tests/unit/test_conftest_console_ctrl_guard.py
  reason: 'revert: these pulled in a huge cascading doc scope closure via unrelated
    pre-existing frob:tests/doc bindings in src/frob/tickets/_land.py; this ticket
    touches only test files, keep scope narrow and handle SCOPE002 via targeted waivers
    instead'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: tests/unit/test_process_guard.py
  reason: 'revert: these pulled in a huge cascading doc scope closure via unrelated
    pre-existing frob:tests/doc bindings in src/frob/tickets/_land.py; this ticket
    touches only test files, keep scope narrow and handle SCOPE002 via targeted waivers
    instead'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: tests/unit/test_process_pid_liveness.py
  reason: 'revert: these pulled in a huge cascading doc scope closure via unrelated
    pre-existing frob:tests/doc bindings in src/frob/tickets/_land.py; this ticket
    touches only test files, keep scope narrow and handle SCOPE002 via targeted waivers
    instead'
  actor: logan
  at: '2026-09-06'
body_changes:
- mode: append
  reason: BUG002 blocks land on a defect whose repro is a real process-killing crash,
    unsafe to run inside the mutation sweep
  actor: logan
  at: '2026-09-06'
  old_length: 2515
  new_length: 3308
evidence:
- tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_labels_did_not_complete_runs
- tests/ticket_land_suite/test_land_lock.py::TestLandLockHolderMetadataAndTimeout::test_holder_metadata_written_on_acquire
- tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_matches_base_ref_tip_true_for_identical_content
- tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_already_landed_sibling_content_excluded
- tests/system/test_cli_ticket.py::TestTicketAttachNonInteractive::test_attach_without_path_fails_fast_off_tty
- tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Narrow subset of T-3936 (19 Windows-specific CI failures), landing the 4 root-caused and fixed here (of which one is the suite-aborting hang):

1. tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_labels_did_not_complete_runs
   Root cause: this test calls the real tests/conftest.py pytest_sessionfinish
   against fakes, but the hook reads FROB_TEST_HARD_EXIT off the real
   os.environ. windows-latest CI's Test step sets FROB_TEST_HARD_EXIT=1 for
   the whole pytest invocation, so the test's exitstatus=3 fake reached
   os._exit(3) for real, killing the xdist worker mid-suite -- this is why
   Windows CI has been reporting an INCOMPLETE failing set (a floor, not a
   count) rather than a true failure list. Fixed with an autouse fixture
   that clears FROB_TEST_HARD_EXIT / FROB_TEST_MIDRUN_WATCHDOG_SECONDS for
   this module's own real os.environ.

2. tests/ticket_land_suite/test_land_lock.py::test_holder_metadata_written_on_acquire
   Windows msvcrt.locking is mandatory (unlike POSIX flock's advisory
   semantics), so reading the lock file from a second handle while still
   inside the _land_lock() context raises PermissionError on
   windows-latest only. Fixed by moving the read after the context exits.

3-4. tests/test_tickets_mutation_evidence.py (two tests, plus one hardened
   preventively): fixture files written with Path.write_text's default
   newline translation emit CRLF on Windows; _matches_base_ref_tip compares
   raw on-disk bytes against git's LF-normalized blob content, so CRLF
   fixtures never byte-match. Fixed with a _write_lf helper (newline="\n")
   plus core.autocrlf=false in _init_repo.

Verified on Linux by reproducing each platform-specific mechanism directly
(no Windows machine available); re-measurement on real Windows CI still
needed to confirm.

Out of scope, filed separately: T-draft-fe768f82 (land.lock's own
post-acquire _read_land_lock_holder hits the same Windows mandatory-locking
conflict, silently swallowed by a best-effort except OSError -- needs a
src/frob/tickets/_land.py fix).

T-3936 remains open and in-progress for the other 15 of 19 Windows
failures (land_core/wip git-semantics, profile_boundary positive controls,
the stdout/tty purity pair in worktree_guard/cli_ticket, rapid_sweep_suite,
arch_suite, strata_gil, telemetry, fuzz, evidence_cli, ticket_leases,
lint_diff_attribution) plus the confirmation that the hang was the actual
blocker for measuring the true Windows failure count.

frob:waive BUG002 reason="the designated repro test hangs/crashes for real (a genuine os._exit(3) call) when FROB_TEST_HARD_EXIT=1 is set without the fix, which is the actual production defect this ticket fixes -- it cannot be safely reproduced inside the automated mutation-evidence sweep (which expects a mutated-code run to merely fail, not kill its own subprocess), and running the repro manually with that env var set was how the root cause was confirmed on Linux in the first place (documented in the fix commit message). Verified manually: at main (no autouse fixture), setting FROB_TEST_HARD_EXIT=1 and invoking the real pytest_sessionfinish hook this test exercises calls os._exit(3) for real; at the fix, the autouse fixture clears the env var first and the hook returns normally."
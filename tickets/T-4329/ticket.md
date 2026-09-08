---
id: T-4329
title: test_frob_self_model.py self-scan tests missing from conftest heavy grouping
  cause concurrent full-repo scans that OOM-crash win32 xdist
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
- tests/unit/test_conftest_stackdump.py
scope_breadth_ack: true
scope_breadth_ack_reason: tests/conftest.py is a large shared fixture file with pre-existing
  frob:tests/frob:doc directives (run_bounded_subprocess, pytest_configure, pytest_sessionfinish,
  _reset_parse_cache_before_test) unrelated to this ticket's actual change (pytest_collection_modifyitems's
  self-scan xdist grouping); SCOPE002 full closure over those pre-existing directives
  cascades into unrelated files and, transitively, an entire unrelated subsystem (src/frob/mutate/*,
  docs/modules/mutate.md) -- narrower scope for the fix itself (tests/conftest.py,
  tests/unit/test_conftest_stackdump.py, both actually touched) plus this ack is the
  correct-sized boundary
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/integration/test_gitlog.py
  reason: 'SCOPE002: these test files carry frob:tests coverage for pre-existing conftest.py
    symbols (run_bounded_subprocess, pytest_configure, _reset_parse_cache_before_test,
    pytest_collection_modifyitems, pytest_sessionfinish); the scope gate requires
    them added whenever tests/conftest.py is in a ticket''s scope, regardless of which
    symbol the ticket''s own edit touches'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_mutate_journal.py
  reason: 'SCOPE002: these test files carry frob:tests coverage for pre-existing conftest.py
    symbols (run_bounded_subprocess, pytest_configure, _reset_parse_cache_before_test,
    pytest_collection_modifyitems, pytest_sessionfinish); the scope gate requires
    them added whenever tests/conftest.py is in a ticket''s scope, regardless of which
    symbol the ticket''s own edit touches'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_conftest_parse_reset.py
  reason: 'SCOPE002: these test files carry frob:tests coverage for pre-existing conftest.py
    symbols (run_bounded_subprocess, pytest_configure, _reset_parse_cache_before_test,
    pytest_collection_modifyitems, pytest_sessionfinish); the scope gate requires
    them added whenever tests/conftest.py is in a ticket''s scope, regardless of which
    symbol the ticket''s own edit touches'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_conftest_stackdump.py
  reason: 'SCOPE002: these test files carry frob:tests coverage for pre-existing conftest.py
    symbols (run_bounded_subprocess, pytest_configure, _reset_parse_cache_before_test,
    pytest_collection_modifyitems, pytest_sessionfinish); the scope gate requires
    them added whenever tests/conftest.py is in a ticket''s scope, regardless of which
    symbol the ticket''s own edit touches'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_conftest_suite_result_status.py
  reason: 'SCOPE002: these test files carry frob:tests coverage for pre-existing conftest.py
    symbols (run_bounded_subprocess, pytest_configure, _reset_parse_cache_before_test,
    pytest_collection_modifyitems, pytest_sessionfinish); the scope gate requires
    them added whenever tests/conftest.py is in a ticket''s scope, regardless of which
    symbol the ticket''s own edit touches'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/mutate/__init__.py
  reason: 'SCOPE002 closure: tests/test_mutate_journal.py (already required in scope
    for its conftest.py::pytest_configure coverage) also tests these mutate-journal
    symbols; pre-existing frob:tests coverage unrelated to this ticket''s actual fix,
    added only to satisfy scope closure'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: src/frob/mutate/_journal.py
  reason: 'SCOPE002 closure: tests/test_mutate_journal.py (already required in scope
    for its conftest.py::pytest_configure coverage) also tests these mutate-journal
    symbols; pre-existing frob:tests coverage unrelated to this ticket''s actual fix,
    added only to satisfy scope closure'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: src/frob/mutate/__init__.py
  reason: 'revert: SCOPE002 closure on these pre-existing, unrelated conftest.py directives
    cascades into whole unrelated subsystems (mutate module + its docs); use frob
    ticket scope-ack instead per SCOPE002''s own documented escape hatch (T-4310)'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: src/frob/mutate/_journal.py
  reason: 'revert: SCOPE002 closure on these pre-existing, unrelated conftest.py directives
    cascades into whole unrelated subsystems (mutate module + its docs); use frob
    ticket scope-ack instead per SCOPE002''s own documented escape hatch (T-4310)'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: tests/integration/test_gitlog.py
  reason: 'revert: SCOPE002 closure on these pre-existing, unrelated conftest.py directives
    cascades into whole unrelated subsystems (mutate module + its docs); use frob
    ticket scope-ack instead per SCOPE002''s own documented escape hatch (T-4310)'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: tests/test_mutate_journal.py
  reason: 'revert: SCOPE002 closure on these pre-existing, unrelated conftest.py directives
    cascades into whole unrelated subsystems (mutate module + its docs); use frob
    ticket scope-ack instead per SCOPE002''s own documented escape hatch (T-4310)'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: tests/unit/test_conftest_parse_reset.py
  reason: 'revert: SCOPE002 closure on these pre-existing, unrelated conftest.py directives
    cascades into whole unrelated subsystems (mutate module + its docs); use frob
    ticket scope-ack instead per SCOPE002''s own documented escape hatch (T-4310)'
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: tests/unit/test_conftest_suite_result_status.py
  reason: 'revert: SCOPE002 closure on these pre-existing, unrelated conftest.py directives
    cascades into whole unrelated subsystems (mutate module + its docs); use frob
    ticket scope-ack instead per SCOPE002''s own documented escape hatch (T-4310)'
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-4322 (Windows suite aborts with KeyError: <WorkerController gw5> INTERNALERROR).

MEASURED (CI run 34240795928, windows leg, log saved at
/tmp/claude-1000/-home-logan-projects-frob/79c6402d-b401-4652-bea7-f81df1be9322/scratchpad/win2.log):

  SUITE-RESULT-FAILED: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001 (failed) -- worker died without a timeout dump (300.6s elapsed) -- suspect OOM -- not rescheduled (rerun cap 0 reached)
  SUITE-RESULT-FAILED: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations (failed) -- worker died without a timeout dump (300.4s elapsed) -- suspect OOM -- not rescheduled (rerun cap 0 reached)
  ...
  KeyError: <WorkerController gw5>
  SUITE-RESULT: DID-NOT-COMPLETE exitstatus=3 (INTERNAL-ERROR) ... cause=KeyError: <WorkerController gw5>

ROOT CAUSE IS A DIFFERENT MECHANISM FROM T-3754/T-3757 (both closed/done, do not
re-close against this): those two fixed per-test TIMEOUT kills (a worker
os._exit()d after exceeding pytest-timeout) by skipif-ing the worst offenders and
raising the win32 per-test timeout to 600s. This crash is an OOM kill (worker
died in ~300s, well under even the OLD 120s-per-test default and far under the
1200s frob_self_scan_heavy timeout T-3525 already grants), so raising a timeout
again would not touch it -- confirmed by reading both prior tickets' Done reports
before filing this.

tests/conftest.py's pytest_collection_modifyitems groups every test named in
_SELF_SCAN_HEAVY_NAME_SUBSTRINGS into ONE shared frob_self_scan_heavy xdist_group
so full-repo-scan tests run serially on a single worker instead of each paying
their peak-memory cost concurrently on separate workers (T-1433's own documented
OOM-kill root cause for the identical symptom, "node down: Not properly
terminated").

test_sys_gate_zero_violations IS in that substrings list (it crashed anyway,
gw2, 300.4s) -- but sibling tests in the SAME class
(tests/system/test_frob_self_model.py::TestFrobSelfModel), which read the SAME
session-scoped frob_self_scan_artifacts fixture (a full
build_graph(_REPO_ROOT, ...) scan), are NOT in the substrings list:
  - test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001 (crashed, gw0, 300.6s)
  - test_fragments_module_fs_read_is_declared_not_selfaudit001
  - test_check_admission_exec_sites_are_declared_not_selfaudit001

Because pytest-xdist session fixtures are per-WORKER, not global, any of these
scheduled onto a worker other than the one running test_sys_gate_zero_violations
triggers its OWN independent full-repo build_graph pass concurrently with the
grouped one -- doubling (or more) the peak-memory cost the frob_self_scan_heavy
grouping exists specifically to prevent. Two of these tests dying with "suspect
OOM" on two DIFFERENT workers (gw0, gw2) at the same ~300s mark is consistent
with exactly that: two full-repo scans running at once on a memory-constrained
Windows runner.

The dual OOM kill is also the win32 job's real inciting event for the
KeyError: <WorkerController gw5> xdist INTERNALERROR: xdist's loadscope
scheduler's registered_collections bookkeeping is corrupted once workers die
mid-schedule, and the resulting _assign_work_unit KeyError aborts the WHOLE
session rather than just failing the two OOM'd tests -- which is why the run
reports itself as DID-NOT-COMPLETE / partial / lower-bound rather than a bounded
failing set.

FIX (not made here -- tests/conftest.py is out of T-4322's scope, which is
tests/system/test_public_api_from_wheel.py only): add the three test names above
to _SELF_SCAN_HEAVY_NAME_SUBSTRINGS (or, more robustly, key the grouping off USE
of the frob_self_scan_artifacts fixture rather than a hardcoded name list --
worth considering explicitly, since this is now the second time a real self-scan
test was missing from the hand-maintained list) so every consumer of that shared
session fixture is serialized onto the same worker.

Do not close this by raising a timeout number alone; the crash here is OOM, not
timeout, and a timeout bump would not change memory pressure.

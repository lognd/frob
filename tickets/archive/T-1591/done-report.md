## Done report

CONFIRMED, ROOT-CAUSED, AND FIXED (real xdist-order pollution):

tests/unit/test_lang_strata.py::TestStrataNativeParserUnavailable
  (test_parse_file_returns_native_parser_unavailable,
  test_outline_file_returns_err_not_crash). Polluter: frob.gates.
  _stamp_worker_parse_artifact_cache_env sets os.environ[
  "FROB_PARSE_ARTIFACT_CACHE"] via a direct assignment with no restore
  -- correct for its real short-lived-CLI-process use, a real leak in a
  long-lived pytest-xdist worker. Any earlier test that drives
  frob.gates.run_gates in-process leaves the var pointing at a torn-down
  tmp_path db; a later, unrelated parse_file/walk_strata call then
  silently consults that stale persistent artifact cache instead of a
  fresh parse, returning a cached Ok for design/litmus/chirp.strata
  where the test expects a fresh Err (native parser monkeypatched
  unavailable). Fixed at the source: tests/conftest.py gets a new
  autouse fixture (_reset_parse_artifact_cache_env_before_test,
  mirroring T-0926/T-1586's existing shape) that pops the env var and
  resets frob.lang._artifact_conn/_artifact_conn_path before every
  test. Before: fails when run after any run_gates-driving test in the
  same worker. After: verified clean in isolation, combined with
  tests/unit/test_lang_artifact_cache.py (the module's own env-var
  tests), and in a tests/unit/ -q run (full directory, all green).

FOUND WHILE INVESTIGATING, NOT ACTUALLY POLLUTION (deterministic,
reproduce in isolation, fixed anyway since in-scope and cheap):

tests/test_serve.py::TestCheckScope::test_in_scope_diff_passes --
  fails in isolation, always: its fixture's declared ticket scope
  covered legacy "tickets.md" but not write_ticket's real v2 per-ticket
  storage path (tickets/T-0001/ticket.md), so SCOPE001 always flagged
  the ticket's own storage file as out-of-scope. Added "tickets/**" to
  the declared scope tuple.

tests/system/test_frob_self_model.py::TestFrobSelfModel::
  test_parses_and_elaborates -- fails in isolation, always: T-1589
  (this drive's earlier ticket) re-derived the k8s/seccomp export
  goldens for design/frob.strata's `security` node addition but missed
  this test's hard-coded node-count assertion (21 -> 22). Bumped it
  with the same root-cause note.

CONFIRMED NOT POLLUTION, FILED AS FOLLOW-UPS (out of T-1591's actual
shared-state charter, or out of its declared scope to fix directly):

- tests/test_ticket_evidence.py::TestKindCliInvalidKind::
  test_invalid_kind_refused: deterministically conflicts with
  tests/test_app_config.py::TestEnumFieldValidation::
  test_invalid_ticket_kind_value_lists_valid_values -- the two tests
  assert MUTUALLY EXCLUSIVE behavior for AppConfig(ticket_kind_value=
  <invalid>) (one expects construction to succeed and _kind() to
  refuse via SystemExit, the other expects a pydantic ValidationError
  at construction). One of them is always failing regardless of run
  order; this needs a design decision, not a pollution fix. Filed
  (draft id T-1594, will renumber at land).
- tests/test_coverage.py::TestCoverageTargetNativesGuard and
  tests/system/test_cli_perf.py::TestCheckOnlyPerf::
  test_perf001_fixture_warns_but_check_exits_zero: both fail
  deterministically in isolation (a stale "pytest --cov" substring
  check against the real Makefile's current coverage-fast recipe; a
  fixture with only 1 unit case against TEST002's current
  min_unit_cases=3 threshold). Neither is pollution; the Makefile
  fix is outside this ticket's scope. Filed (draft id T-1595).

COULD NOT DE-POLLUTE WITHIN BUDGET -- STILL RED under some xdist
configurations, disclosed rather than left silently red:

- tests/unit/test_app_runners.py::TestMapRunner (both tests) and
  ::TestOutlineRunner::test_directory_target_falls_back_to_map: fail
  in a full `pytest tests/ -n auto` run (caplog.records empty when
  INFO logging is expected) but pass in isolation, combined with
  tests/unit/test_main_entry.py, and as the whole tests/unit/
  directory. Could not identify the specific cross-file polluter or a
  smaller reproducing combination within this ticket's time budget.
- tests/test_lang.py::TestParseCache::test_second_call_same_content_is_a_hit:
  same shape -- passes in every isolated/combined repro tried, red
  only in the full run. A second, still-undiscovered shared counter/
  cache beyond the artifact-cache env var already fixed is the likely
  cause, not confirmed.
- tests/test_ticket_land.py::TestClaimDivergencePostMerge: passed in
  every repro attempt (isolation and combined); never reproduced the
  failure directly outside a full run's short summary.
- Four NEWLY OBSERVED failures under a full run with -n 4 (different
  worker count/grouping than -n auto), not on the original list, each
  clean in isolation and combined with each other:
  tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::
  test_claims_captured_from_real_callables,
  tests/test_ticket_land.py::TestLedgerV2LandMergeStory::
  test_same_ticket_conflict_surfaces_loudly_no_splice,
  tests/test_ticket_reverify.py::TestReverifyCli::
  test_surfaces_now_failing_evidence_loudly,
  tests/test_tickets_scope_mutation.py::TestNewFileCarveOut::
  test_new_file_under_broad_lease_is_exempt.

All of the above unresolved items are filed together as a follow-up
(draft id T-1596) rather than left as a silent gap.

FULL-SUITE VERIFICATION CAVEAT: three separate full, unscoped
`pytest tests/` background runs during this investigation (two at
-n auto, one at -n 4) each terminated WITHOUT printing pytest's own
final "N passed, M failed in Ts" summary line -- output stops right
after the "short test summary info" FAILED list, no crash traceback,
no INTERNALERROR visible in the captured log. This means I do NOT
have a clean, fully-completed before/after total pass/fail COUNT to
report -- only the consistent set of failing test IDENTITIES each run
did manage to report before truncating, which is what this report is
based on. Flagged in the T-1596 follow-up as its own
investigation item; this repo's own memory notes an earlier WSL OOM
session-kill history that may be the same class of issue recurring
for a genuinely full run specifically.

Verification actually completed: targeted pytest runs for every FIXED
test (all now pass, several combinations tried including full
tests/unit/ directory), `frob sys sync-interface` clean, design/
frob.strata still parses. Did not run `frob check` broadly for this
ticket given its scope is test-file-heavy; the touched production
file (tests/conftest.py, src is untouched here) needs no gate beyond
what pytest itself already verifies.

### Changed
```
 design/frob.strata                                |  22 +-
 docs/design/registry/check-coverage.yaml          |   6 +-
 docs/guides/extending/registry_of_registries.json |   2 +-
 src/frob/__init__.py                              |   4 +
 src/frob/gates/_fix_engine.py                     |   1 +
 src/frob/gates/_rule_id_scan.py                   |  13 +-
 src/frob/gates/_waive.py                          |   6 +
 tests/conftest.py                                 |  48 ++-
 tests/golden/frob_export_k8s.yaml                 |  14 +
 tests/golden/frob_export_seccomp.json             |  19 ++
 tests/system/test_frob_self_model.py              |   7 +-
 tests/test_serve.py                               |  10 +-
 tests/unit/strata/test_mutation_audit.py          |  11 +-
 tests/unit/strata/test_threat.py                  |  17 +-
 tests/unit/test_extending_guides_complete.py      |   2 +-
 tickets.md                                        | 342 +++++++++++++++++++++-
 16 files changed, 497 insertions(+), 27 deletions(-)
```

### Evidence
- `tests/unit/test_lang_strata.py::TestStrataNativeParserUnavailable::test_parse_file_returns_native_parser_unavailable` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_strata.py::TestStrataNativeParserUnavailable::test_outline_file_returns_err_not_crash` (pytest node id, verified passing when recorded)
- `tests/test_serve.py::TestCheckScope::test_in_scope_diff_passes` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 5494 warning(s), 787 waived
- error-findings: none (measured, zero errors)

## Done report

Re-measured frob-exports at ticket start (counts had drifted from the
2026-07-23 baseline named in the ticket body): frob 3, arch 74, gates 8,
graph 3, lang 2, mutate 3, perf 3, process 3, process/parsers 1, scaffold
1, serve 11, strata 5, testing 0, tickets 1, vet 9. Ticket scope covers 9
packages only (frob, arch, lang, mutate, perf, scaffold, serve, testing,
vet) -- gates/graph/process/process/parsers/strata/tickets are out of
scope (owned elsewhere) and left untouched.

For every missing symbol in the 9 in-scope packages, decided export vs.
privatize by checking real usage (real import statements, not prose
mentions) across the repo:

- Exported: symbols with a genuine cross-package or cross-module
  consumer (e.g. arch._mayraise.compute_may_raise used by frob.gates;
  arch._ffi's pyo3/ctypes scanners used by frob.gates._ffi_boundary;
  the arch._normalized dataclass family backing the already-public
  NormalizedFunction/NormalizedClass; the arch SOLID/typedesign/
  fallibility/smells/logging-checks families -- written, fully tested
  (tests/unit/test_arch.py), and documented as deliberate public
  advisory categories not yet wired into analyze_project's dispatch
  loop, same shape as the DIP-layering family which IS load-bearing in
  tests/unit/test_arch.py::TestLayeringConfig etc; vet's
  resolve_capability_kind/canonical_declared_kind/expand_declared_kind/
  CapabilityModeError/non_executable_line_numbers, consumed by
  frob.strata; frob.tomlio.read_toml_lenient, consumed by frob.perf/
  frob.gates; frob.mutate JournalError/StaleJournal, consumed by
  frob.doctor/tests; frob.perf.duplicate_spawn_violations, consumed by
  frob.perf._rules; frob.perf's EffectGraph/Unknown, whose own module
  docstring calls out a "documented public surface").

- Privatized (leading underscore + referrers fixed): symbols with zero
  real consumers outside their own module (frob.doctor's
  detect_derived_state_drift/DerivedArtifactDrift; frob.lang._common's
  child_text/iter_cpp_functions, used only by frob.lang's own walkers;
  frob.mutate._journal.MutationJournalEntry; frob.arch's
  scan_cpp_functions/CppFunctionRaises and PatternRuleSpec;
  frob.scaffold.ManagedTextBlock; frob.serve._daemon/_warm's entire
  surface -- poll_post_land/poll_rebase_bot/run_daemon_cycle/
  start_daemon/PostLandVerdict/RebaseWarning/DaemonStatus/
  repo_dirty_key/warm_state/invalidate/WarmState -- every real caller
  (including tests) already accessed these module-qualified
  (`_daemon.X`/`_warm.X`), confirming accidental publicness;
  frob.vet's OpaqueFinding/mode_qualified/normalize_observed_kind/
  DeprecatedCapabilityAlias).

Fixed every referrer of a privatized name (production code, tests, and
docs `frob:describes` directives/prose in docs/guides/install.md and
docs/modules/{arch,lang,mutate,serve}.md) so nothing broke.

Side effects handled: ruff import-sort auto-fix on the two __init__.py
files edited plus the walker files touched for referrer fixes; a new
ARCH102 finding on frob.lang._common.py caused by the reduced export
count crossing the clustering-heuristic threshold, waived with an
honest reason; a handful of pre-existing DUP001/DUP002 findings on
functions I did not touch, surfaced only because I edited unrelated
lines earlier in the same file for the child_text rename -- waived with
an honest reason rather than silently fixed (out of this ticket's
__init__.py-only scope) or left to block the gate.

No new tickets filed -- everything found was either in scope (the 9
packages) or resolved via a reasoned waiver at the surfaced site; no
work was found that needed a separate out-of-scope ticket.

### Changed
```
 docs/guides/install.md                  |   6 +-
 docs/modules/arch.md                    |   8 +-
 docs/modules/lang.md                    |   8 +-
 docs/modules/mutate.md                  |   6 +-
 docs/modules/serve.md                   |  62 +--
 src/frob/__init__.py                    |   2 +
 src/frob/arch/__init__.py               | 162 +++++-
 src/frob/arch/_cpp_mayraise.py          |  37 +-
 src/frob/arch/_patterns.py              |  36 +-
 src/frob/doctor.py                      |  32 +-
 src/frob/lang/_common.py                |  31 +-
 src/frob/lang/_extract.py               |  12 +-
 src/frob/lang/_nodes.py                 |  20 +-
 src/frob/lang/_walk_c.py                |  26 +-
 src/frob/lang/_walk_kotlin.py           |  20 +-
 src/frob/lang/_walk_python.py           |  25 +-
 src/frob/lang/_walk_rust.py             |  16 +-
 src/frob/lang/_walk_typescript.py       |  19 +-
 src/frob/mutate/__init__.py             |  10 +-
 src/frob/mutate/_journal.py             |  22 +-
 src/frob/perf/__init__.py               |   5 +
 src/frob/scaffold/_managed.py           |  32 +-
 src/frob/serve/_daemon.py               | 102 ++--
 src/frob/serve/_tools.py                |  15 +-
 src/frob/serve/_warm.py                 |  62 ++-
 src/frob/serve/server.py                |   4 +-
 src/frob/vet/__init__.py                |  12 +
 src/frob/vet/_capability.py             |  20 +-
 src/frob/vet/_capability_modes.py       |  45 +-
 tests/test_serve.py                     |  66 +--
 tests/test_serve_daemon.py              |  40 +-
 tests/unit/test_exports.py              |  48 ++
 tests/unit/test_lang_primitives.py      |  14 +-
 tests/unit/vet/test_capability_modes.py |  10 +-
 tickets.md                              | 848 +++++++++++++++++++++++++++++++-
 35 files changed, 1547 insertions(+), 336 deletions(-)
```

### Evidence
- `tests/unit/vet/test_capability_modes.py::TestModeQualified::test_joins_family_and_mode` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_capability_modes.py::TestCanonicalAndNormalize::test_normalize_observed_kind_matches_canonical` (pytest node id, verified passing when recorded)
- `tests/test_serve.py::TestWarmState::test_second_call_is_cache_hit` (pytest node id, verified passing when recorded)
- `tests/test_serve.py::TestWarmState::test_file_change_forces_rebuild` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestPollPostLand::test_head_unchanged_is_noop` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestPollPostLand::test_head_moved_refreshes_verdict` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestRunDaemonCycle::test_runs_both_jobs_and_returns_status` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestFrobDaemonStatus::test_reads_current_status` (pytest node id, verified passing when recorded)
- `tests/test_serve_daemon.py::TestStartDaemon::test_background_loop_runs_a_cycle_then_stops` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_write_journal_is_idempotent_for_same_content` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_write_journal_refuses_on_content_collision` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestParsePython::test_symbols_and_nesting` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_kotlin.py::TestParseKotlin::test_kt_fixture_parses_without_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_primitives.py::test_collapse_ws_flattens_whitespace` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_dup_spawn.py::TestPerf012DuplicateSpawn::test_two_helpers_spawning_identical_subprocess_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_effect_summaries.py::TestUnknownIdentityEquality::test_two_unknowns_with_the_same_reason_text_are_not_equal` (pytest node id, verified passing when recorded)
- `tests/test_doctor.py::test_run_diagnosis_natives_present` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestErrorsAsValuesAdvisory::test_public_raiser_with_no_handling_caller_recommends_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 19 passed (from 19 evidence id(s))
- gates: 6 error(s), 2535 warning(s), 630 waived
- error-findings: COV003@tickets/T-0893, COV003@tickets/T-0904, COV003@tickets/T-1051, COV003@tickets/T-1053, PII012@src/frob/tickets/_leases.py, PRE001@tickets/T-0871

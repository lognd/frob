## Done report

T-0570 landed verify_derived_state (frob.doctor) but nothing in frob check
ever consulted it, so a corrupt .frob cache/baseline/coverage artifact
would silently feed wrong data into the graph/dup/gates pipeline instead
of failing loudly. This ticket wires the precheck into every run_check*
entry point (run_check, run_check_cpp, run_check_rust, run_check_ts) so a
present-but-corrupt derived artifact short-circuits the whole check run
with a single derived-state-integrity ERROR ToolResult (diagnostic code
DERIVED001) before any stage is dispatched.

Design decision: absent vs corrupt. verify_derived_state already treats a
missing artifact as healthy (T-0570); this ticket preserves that -- only
present-but-invalid (fails the sqlite-magic-header or json.loads check)
trips the new precheck. A fresh clone or post-clean tree never sees this
fire.

Design decision: where the check runs. The first implementation put the
check inside _run_gates (the shared choke point every run_check* variant
calls). That was wrong: arch/dup/gates all read or rebuild the same
.frob/cache.db concurrently inside frob check's ThreadPoolExecutor batch,
so fingerprinting from inside one of those stages raced the others' live
writes -- a cache mid-rebuild, observed by another thread, reads as
"corrupt" (truncated bytes) when it is merely momentarily in-progress.
This surfaced for real: TestCheckBuildsGraphOnce's existing
test_run_check_calls_build_graph_exactly_once started failing
intermittently once the in-_run_gates version was wired in, because the
gates stage's integrity check sometimes observed arch's still-empty
cache.db and refused before build_graph ran at all. The fix was to move
the check to frob.check._derived_state_integrity_result, called once,
synchronously, in each run_check* entry point BEFORE any concurrent stage
is dispatched -- this serializes the integrity read ahead of every writer
and is also cheaper (one fingerprint pass per frob check run, not one per
gate family). _run_gates's docstring was updated to explain the
precondition is now guaranteed by its caller, not itself.

What changed:
- src/frob/check/__init__.py: new _derived_state_integrity_result(root)
  helper; wired as the first thing run_check (via
  _run_check_with_skips), run_check_cpp, run_check_rust, and
  run_check_ts all do, before dispatching any stage.
- src/frob/check/_python.py: _run_gates's docstring updated to note the
  precondition is enforced by its caller now (no functional change to
  this file beyond the docstring).
- tests/unit/test_check.py: new TestDerivedStateIntegrityGate class
  (corrupt artifact fails closed with no stage dispatched; absent
  artifact is not a violation) plus a scope extension (this file was
  outside T-0603's original scope, added via frob ticket scope --add).
- docs/modules/gates.md: new "DERIVED001 (T-0603)" subsection explaining
  the mechanism, the absent-vs-corrupt distinction, why it is not one of
  _KNOWN_GATE_RULES (a check-orchestration precondition, not a waivable
  Violation), and the race the up-front placement avoids. Scope extended
  to cover this file for the same reason (frob:doc + docs in the same
  change).

Mutant kill (hand-verified, T-0603): temporarily removed the
integrity-precheck short-circuit from run_check's _run_check_with_skips
(restoring the direct call into _python_tasks with no guard) and reran
tests/unit/test_check.py -k DerivedStateIntegrity -- the corrupt-artifact
test failed with the expected AssertionError from its
monkeypatched-run_gates tripwire ("no check stage may run once a derived
artifact has already failed the integrity precheck"), confirming the test
actually exercises the wiring rather than passing vacuously. Restored the
real implementation afterward and reran green.

Evidence executed and observed:
- tests/unit/test_check.py::TestDerivedStateIntegrityGate::test_corrupt_artifact_fails_closed_before_any_stage_runs
- tests/unit/test_check.py::TestDerivedStateIntegrityGate::test_absent_artifact_is_not_a_violation
- tests/unit/test_check.py::TestCheckBuildsGraphOnce::test_run_check_calls_build_graph_exactly_once
  (the regression this ticket's initial design caused and then fixed;
  bound as evidence because it is what actually caught the race)
- Full targeted file: uv run pytest tests/unit/test_check.py -q -o addopts=""
  -> 42 passed
- Full verify list from the ticket brief (tests/system/test_cli_check.py,
  tests/test_check_coverage_registry.py, tests/test_gates.py,
  tests/test_gates_fmt_directives.py, tests/test_gates_mutation_evidence.py,
  tests/test_gates_ratchet.py, tests/test_gates_tick005.py,
  tests/test_gates_tickets_hygiene.py, tests/test_gates_worktree_lease.py,
  tests/unit/test_check.py, tests/unit/test_check_tool_unavailable.py)
  -> 560 passed, 3 failed. The 3 failures are pre-existing and unrelated
  to this change, already tracked in tickets.md before this ticket
  started: TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
  (documented order-dependent capsys/logging flake, T-0818) and both
  TestCheckCoverageRegistryFile/TestExhaustivenessGateOverRealCheckCoverage
  failures (missing CHK-GATE-TEST016 registry entry, pre-existing REG010
  gap already filed in tickets.md, "gate: TEST016 missing CHK-GATE-TEST016
  registry entry (REG010, pre-existing)"). Confirmed unrelated: git diff
  --name-only shows only src/frob/check/__init__.py,
  src/frob/check/_python.py, tests/unit/test_check.py, docs/modules/gates.md,
  and tickets.md touched by this ticket -- none of the failing tests'
  underlying files are in that set.

Gates: frob check --only lint/static/gates-fast/gates-native/gates-security
--ticket T-0603 all clean (0 errors) after adding the frob:ticket edge on
the new test class, correcting the frob:tests qualname separator
(Class.method, not Class::method), and extending scope to
tests/unit/test_check.py and docs/modules/gates.md (both needed for the
frob:doc/frob:tests obligations on the new symbol). git diff main
--diff-filter=D --stat is empty.

Deviations from the initial plan: none in outcome, but the implementation
went through one design correction mid-ticket (in-_run_gates check ->
up-front precheck in each run_check* entry point) after the concurrency
race described above was caught by existing test coverage, not new
coverage written for this ticket. No scope other than the two
documentation/test-file additions above was widened.

Filed: none (no out-of-scope discoveries beyond the two already-tracked
pre-existing failures noted above).

### Changed
```
 docs/guides/install.md          |  51 +++++-
 docs/modules/gates.md           |  45 ++++++
 src/frob/check/__init__.py      |  90 +++++++++++
 src/frob/check/_python.py       |  10 ++
 src/frob/doctor.py              | 165 ++++++++++++++++++-
 tests/system/test_cli_doctor.py | 106 +++++++++++++
 tests/unit/test_check.py        |  51 ++++++
 tickets.md                      | 341 +++++++++++++++++++++++++++++++++++++++-
 8 files changed, 841 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/unit/test_check.py::TestDerivedStateIntegrityGate::test_corrupt_artifact_fails_closed_before_any_stage_runs` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestDerivedStateIntegrityGate::test_absent_artifact_is_not_a_violation` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestCheckBuildsGraphOnce::test_run_check_calls_build_graph_exactly_once` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

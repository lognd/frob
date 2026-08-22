## Done report

Audit only, no code change (frob:no-behavior-change).

Denominator: 6 files named in T-1654's own body as unaudited for the
T-1433/T-1635 real-repo-root `build_graph` xdist contention shape --
tests/test_waive_gate.py, tests/test_graph.py, tests/test_dup.py,
tests/test_gates.py, tests/test_secrets_gate.py, tests/test_vet.py.
Every `build_graph`/`find_clones` call site in all 6 files was read
directly (not grep-inferred) to classify it as real-repo-root vs.
isolated tmp_path.

Classification:
- tests/test_graph.py: 0 real-repo-root build_graph calls. CLEAR.
- tests/test_dup.py: 0 real-repo-root build_graph calls (the one
  real-source-reading fixture at line 724 copies files INTO tmp_path
  before calling build_graph(tmp_path, ...)). CLEAR.
- tests/test_secrets_gate.py: 0 build_graph calls against a real root
  (its one build_graph call at line 135 targets tmp_path / "repo"; the
  `secrets_gate(root)` calls against the real repo are a plain regex
  file walk, no graph build, no derived.lock involvement). CLEAR.
- tests/test_vet.py: 0 real-repo-root build_graph calls (both
  build_graph calls, lines 6455/6513, target tmp_path; the repo_root
  usages elsewhere copy source files into tmp_path/fake dirs first).
  CLEAR.
- tests/test_waive_gate.py: 2 real-repo-root build_graph calls, same
  shape as T-1635's fix (`_load_inputs(GateConfig(root=_REPO_ROOT))`
  internally builds the graph against the live repo):
  - TestWaive006RealRepo::test_zero_errors_on_real_repo
  - TestWaive007RealRepo::test_zero_findings_on_real_repo
- tests/test_gates.py: 2 real-repo-root build_graph calls out of its
  many build_graph call sites (the rest all target tmp_path / "repo"):
  - TestProtocolSummaryGate::test_real_repo_scan_runs_end_to_end_without_crashing
  - TestOptInGates::test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses

Total candidates: 4 of 6 files clear, 4 tests across the remaining 2
files share the exact evidence shape T-1635 fixed.

Verification attempted: ran all 4 candidates together under
`pytest -n 2 --dist loadscope` (foreground, budget-bound per playbook
section 3c -- a real `pytest -n auto` full-suite reproduction is a
COORDINATOR-only step per sections 3c/6b and was not attempted here).
All 4 passed with no node-down/timeout; `--durations=10` showed each is
genuinely heavy (66.01s, 28.64s, 23.28s, 19.46s respectively) -- the
same cost profile T-1635 targeted, but a 4-test/2-worker scoped run
does not reproduce the actual contention/OOM shape (queueing on
`derived_state_lock` or peak-memory concurrency), which needs many
concurrent full-repo scans under real full-suite load. This does NOT
meet the evidentiary bar T-1635 itself used (a real pytest -n auto
full-suite run tripping pytest-timeout with a faulthandler trace
showing derived_state_lock contention) -- per this repo's own
positive-control doctrine and the ticket's own instruction not to add
names speculatively, `_SELF_SCAN_HEAVY_NAME_SUBSTRINGS` was left
UNCHANGED.

Filed: T-2762 ("Reproduce/fix xdist contention for 4
real-repo build_graph tests found by T-1654 audit"), scope
tests/conftest.py, carrying the 4 node ids and the exact reproduction
step (real `pytest -n auto` full-suite pass) needed to close the loop
-- a coordinator-run verification, not something a dispatched sub-agent
can perform in its foreground budget.

Changed: none (audit-only; tests/conftest.py's
_SELF_SCAN_HEAVY_NAME_SUBSTRINGS list is unchanged).
Evidence: none applicable -- no code/test change made; frob:no-behavior-
change declared.
Filed: T-2762 (renumbers at land).
Gates: N/A, no-behavior-change.

### Changed
```
 tickets/T-1654/ticket.md           |  7 +++-
 tickets/T-1661/ticket.md           | 11 ++++-
 tickets/T-2762/ticket.md | 83 ++++++++++++++++++++++++++++++++++++++
 3 files changed, 98 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 15 error(s), 2141 warning(s), 708 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md

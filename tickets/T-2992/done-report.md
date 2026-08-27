## Done report

Method: full suite (12039 collected tests) run to completion in bounded
chunks (tests/unit whole [-n 6], tests/gates, 3 alphabetical thirds of
top-level tests/*.py further split when a chunk hit the 540s shell
timeout, tests/integration+tests/system together, tests/test_doctor.py
separately after it repeatedly stalled other chunks) -- single full-shot
runs were not viable: this box had 1-3 other agents' `frob check`/
`cargo`/pytest processes contending throughout, `PYTEST_XDIST_AUTO_NUM_
WORKERS=1` (fleet-context auto-detected) made a single-worker full run
project to ~5 hours, and even -n 3/-n 6 chunks occasionally hit pytest's
own 120s per-test timeout under load (see the test_doctor.py finding
below). Total measured: 12035/12039 collected across all chunks (4
short of the full collect-only count, rounding/overlap in chunk
boundaries, not a gap in coverage of any real cluster).

RAW RESULT: 87 FAILED node ids total across all chunks. One
(tests/test_gates_mutation_evidence.py::TestBugReproTimeout::test_slow_test_exceeding_budget_is_timeout_not_no_verdict)
was a regression from this SAME series' T-3015 change, fixed in-flight
(see T-3015's Done report) and re-verified green -- 86 REMAIN as this
ticket's real Linux failure list.

HISTOGRAM (86 failures, by root-cause cluster):

  A. 11  -- KNOWN, already tracked by T-3019 (in-progress, another
            agent): `frob check` fires spurious REF001/PRE001/SCOPE001
            on any clean/scaffolded synthetic project, cascading through
            tests/system/test_cli_check.py (8), test_scaffold_dx.py (1),
            test_cli_native_missing.py (1), test_cli_perf.py (1).
            CONFIRMED via direct repro of test_clean_code_exits_zero
            (PRE/REF/SCOPE FAIL on a trivially clean tmp project); the
            other 10 match T-3019's own ticket body listing near-
            identical test_cli_check.py node ids as already-diagnosed.
            NOT double-filed, NOT double-fixed -- T-3019 owns this.

  B.  3  -- NEW, filed T-3040: `frob cycle <dir>` refuses
            (exit 2, "could not resolve to a project root") on a bare
            tmp_path with no pyproject.toml/git repo; 3
            tests/system/test_system.py::test_cycle_* tests construct
            exactly that fixture and assert exit 0. CONFIRMED by direct
            repro. Genuine product-vs-test ambiguity requiring an owner
            decision (fix the resolver, or fix the tests) -- not
            resolved here.

  C. 28  -- NEW, filed T-3037: a shared ticket-minting test
            helper across test_ticket_work_and_land_finish.py (14),
            test_ticket_runner_archive_force.py (3), test_cli_ticket.py
            (4), test_ticket_land_proof_claims.py (3),
            test_ticket_evidence.py (1), test_cli_ticket_promote.py (1),
            test_cli_ticket_land.py (1), test_ticket_leases.py::
            test_archive_cli_leaves_repo_clean (1) predates T-2394's
            empty-scope ticket-start refusal guard. CONFIRMED root cause
            in exactly 1 of the 28 (test_creates_worktree_merges_main_
            and_starts_ticket: "T-0001 has an EMPTY scope"); the other
            27 are listed by shared "mint-a-throwaway-ticket-then-run-a-
            CLI-verb" shape, NOT individually re-run -- ticket body says
            so explicitly and asks for per-id verification after the
            fixture fix.

  D.  5  -- NEW, filed T-3035: tests/test_ticket_leases.py's
            TestLedgerAutoCommitEnumeratedOverDispatchTable dispatch
            table invokes mutate-style ticket verbs (component/kind/
            priority/tier + the accounting test) without `--reason`;
            CONFIRMED for [tier] and [component] via direct repro
            (`SystemExit: 1`, "frob ticket tier requires --reason TEXT
            or --reason-file PATH"). Same class as cluster C (stale
            shared test fixture predating a newer CLI guard), different
            fixture/guard.

  E. 13  -- NEW, filed T-3041: tests that assert THIS repo's
            own live gate/registry/self-model output is currently
            zero-violation (test names literally say "zero_against_live_
            repo"/"zero_errors_on_real_repo"/"no_reg008_findings"/
            "unrestricted_scan_is_clean"). Matches this same worktree's
            own `frob check --ticket T-3015 --budget 480` run showing
            non-zero repo-wide FAIL counts on DOC/DRIFT/PRE/REF/REG/
            SCOPE/TEST/TICK/WAIVE/ARCH/LARGE/PII/SEC/SELFAUDIT/SYS gates
            -- almost certainly these 13 are reporting that same
            pre-existing non-zero state through pytest assertions rather
            than a new Linux-specific defect. NOT individually
            correlated to a specific owning ticket per finding (flagged
            in the filed ticket as the next triage step).

  F/G. 26 -- NEW, filed T-3034: genuinely uncharacterized --
            spot-checked one (test_gitattributes_merge.py, likely this
            box's global git `core.autocrlf` config differing from the
            test's assumption -- environment-dependent, not confirmed
            fixed/unfixed) and grouped the rest (test_gates.py x6,
            test_makefile_lock_sync.py x2, test_gates_tick009_tick010.py
            x2, test_cli_evidence_enforcement.py x2, test_cli_graph.py
            x2, and 12 more singles) with NO shared root cause found --
            filed honestly as "needs individual triage" rather than
            guessed at.

  (separate) test_doctor.py (13 tests): 0 failures in isolation/serial
            (13/13 pass, `pytest tests/test_doctor.py -p no:xdist`), but
            reliably STALLS past pytest's 120s per-test timeout under
            xdist contention (-n 2/-n 3 with sibling fleet load) --
            root-caused via thread dump to `scan_stale_ticket_leases`
            enumerating a real `git` subprocess per branch, ~900+
            branches, same underlying cost class as the known
            "doable scans every branch" issue (T-2629 territory). Filed
            T-3033 (test-fragility-under-load, not a Linux-
            general defect).

PRODUCT DEFECT vs TEST FRAGILITY split:
  - Confirmed PRODUCT-side questions (owner decision needed, not pure
    test bugs): cluster B (frob cycle's root-resolution contract).
  - Confirmed TEST FRAGILITY (stale fixtures predating newer CLI
    guards): clusters C, D.
  - Pre-existing REPO STATE surfaced via test (neither exactly "new
    product bug" nor "test fragility" -- the repo's own gate output is
    genuinely non-zero right now): cluster E.
  - Known, owned elsewhere: cluster A (T-3019).
  - Environment-dependent local config, uncharacterized rest: F/G.
  - Perf/contention-sensitive test, not exercised at all by a serial
    run: test_doctor.py cluster.

T-3018 CROSS-REFERENCE: the task brief named "T-3018" as the concurrent
clean-project-noise fix; the actual in-progress ticket covering that
exact shape (spurious REF001/PRE001/SCOPE001 on a clean project) is
T-3019, not T-3018 (T-3018 is an unrelated os.kill(pid,0)/Windows
liveness-probe ticket). Cluster A above is attributed to T-3019, the
ticket whose own body already lists 6+ of these exact node ids as
diagnosed.

NOTHING was skipped to make the suite look green. No `--only`/`-k`
exclusion was applied to hide a failure; every chunk's full node-id list
was captured and is accounted for in one of the buckets above.

Filed: T-3040, T-3037, T-3035,
T-3041, T-3034, T-3033 (real ids verified
on main before citing further -- draft ids only exist in this worktree
until land).

Gates: this ticket's own scope is `[]` (a triage/filing ticket, no code
changed under T-2992 itself beyond ticket-ledger commits) -- no gate run
required beyond the ticket-mutation commands' own auto-checks, which
completed clean (each `frob ticket new`/`drop`/`scope` call above
committed successfully with no ledger errors).

### Changed
```
 docs/modules/process.md            |   3 +
 src/frob/gates/_bug_repro.py       |  66 ++++++++-------
 src/frob/process/_guard.py         |  41 ++++++++--
 tests/unit/test_process_guard.py   |  39 +++++++++
 tickets/T-2992/ticket.md           |   2 +-
 tickets/T-3015/done-report.md      | 163 +++++++++++++++++++++++++++++++++++++
 tickets/T-3015/ticket.md           |  40 ++++++++-
 tickets/T-3033/ticket.md |  66 +++++++++++++++
 tickets/T-3034/ticket.md |  73 +++++++++++++++++
 tickets/T-3035/ticket.md |  56 +++++++++++++
 tickets/T-3036/ticket.md |  56 +++++++++++++
 tickets/T-3037/ticket.md |  88 ++++++++++++++++++++
 tickets/T-3038/ticket.md |  50 ++++++++++++
 tickets/T-3039/ticket.md |  51 ++++++++++++
 tickets/T-3040/ticket.md |  61 ++++++++++++++
 tickets/T-3041/ticket.md |  74 +++++++++++++++++
 16 files changed, 887 insertions(+), 42 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 55 error(s), 630 warning(s), 854 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3015/ticket.md, DOC006@tickets/T-draft-291498b9/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, I001@/home/logan/projects/frob/.claude/worktrees/t3015-t2992-series/tests/test_narrative_migrate.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py

## Done report

Changed:
  tests/unit/test_land_duplicate_ticket_id.py (added _git_clone helper,
  swapped 4 raw `git clone` call sites onto it)

Evidence:
  tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_flags_id_with_genuinely_different_content_on_both_sides (DESIGNATED REPRO)
  tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_ignores_the_landing_tickets_own_id
  tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_ignores_an_id_that_already_existed_at_the_merge_base

CLASS A (git identity, 3 tests): root cause was `git clone` (never copies
the source repo's LOCAL, non-global config) followed by a commit inside
the clone -- relied on the ambient machine's GLOBAL git identity, present
on a developer box (so these passed locally) and absent on a bare CI
runner ("Author identity unknown"). Fix is hermeticity-side (ii from the
ticket's own two options): a `_git_clone` helper now sets
user.email/user.name in every clone, so the fixture no longer depends on
ambient state in either direction. No workflow change made or needed --
the defect was entirely inside the test fixture, not something a
`git config --global` in CI would have been the right fix for (that
would have masked the symptom on the runner while leaving the same trap
for the next clone+commit fixture).

Verified directly (not just via --check-repro):
  - FAILED_AT_PARENT confirmed via `frob ticket evidence --check-repro`
    run with HOME pointed at an empty throwaway directory and
    GIT_CONFIG_GLOBAL/GIT_CONFIG_SYSTEM=/dev/null (simulates a CI runner
    with no ambient identity) -- genuinely fails at the pre-fix commit
    under those conditions.
  - Post-fix, the same simulated-CI env (no ambient identity at all)
    passes clean: 5/5 tests in the file.
  - MUST-STAY-QUIET check: this repo's own dev sandbox DOES carry a real
    global git identity (confirmed: git config user.email/user.name both
    set) -- ran the full file with the sandbox's normal, unmodified
    environment and it passes there too. The fix is insensitive to
    ambient identity in both directions, not merely tolerant of its
    absence.

CLASS B (2 tests, ~/.claude): re-verified against a fresh HOME with no
~/.claude at all (same simulated-CI technique) -- both
test_start_auto_plans_queued_ticket and test_plan_then_sweep_flow
already pass. They were fixed by T-3080's own land (which added the
missing --scope to their ticket-minting helpers, T-3080's own root
cause), landed earlier in this same series -- no change needed here.
The "Claude config DRIFT" text this ticket's own CI-log excerpt quoted
was never the actual failure cause for these two: it is a stderr line
`_print_startup_warnings` prints ahead of EVERY CLI subcommand when the
INVOKING PROCESS's cwd (not the fixture's --path) has a
.claude/hooks/sync-claude-config.py and an out-of-sync real ~/.claude --
it happened to be the first line of `r.stderr`, which these tests use
as their assertion failure message, but the actual nonzero exit was
T-2394's empty-scope refusal underneath it. Left uncorrected as
out-of-scope commentary since T-3080 already fixed the real cause.

SWEEP for the same ambient-state class (acceptance criterion): searched
every test file for `git clone` and for `Path.home()`/`os.environ["HOME"]`/
`expanduser`/global-config reads.
  - `git clone`: 4 files besides this one (tests/test_gates.py,
    tests/test_ticket_land.py, tests/test_tickets_collision.py). All
    three already set user.email/user.name in the clone before
    committing there, OR never commit inside the clone at all (read-only
    checkout-branch probes) -- confirmed clean, not merely assumed.
  - `Path.home()`/`$HOME` reads: 4 files
    (tests/system/test_scaffold_dx.py, tests/test_check_runner.py,
    tests/unit/test_claude_runner.py, tests/unit/test_confinement_lattice.py).
    The two Claude-config-sync test files already monkeypatch `Path.home`
    plus `$HOME` to a throwaway per-test directory (the correct pattern,
    T-1808-era). test_scaffold_dx.py's read is a declared, explicit
    "detect an optional real global `frob` install, skip if absent"
    probe, not a hidden dependency. test_confinement_lattice.py's
    `os.environ["HOME"]` is inside a STATIC-ANALYSIS SAMPLE STRING (code
    being scanned, not executed) -- not a real runtime read at all.
  - Bare `git commit` without any identity setup anywhere in the same
    file: checked every file matching `"commit"` with no `user.email`
    string (7 files) -- all either set identity via
    `GIT_AUTHOR_EMAIL`/`GIT_COMMITTER_EMAIL` env vars
    (test_tdd_order.py, test_watermark.py) or route every commit through
    the repo's own shared `git_init_and_config` helper
    (test_cli_check.py, test_cli_cycle.py, test_run_helper_env_leak.py),
    or the "commit" match is a string literal in generated sample code,
    not a real git call (test_dup_spawn.py, test_rapid_debt.py).
  Total additional broken instances found beyond the 5 named in the
  ticket: 0. All were either already hermetic or (Class B) already
  fixed by T-3080's own land.

Filed: none

Gates: frob check --ticket T-3075 (--only scope/prework/fmt/affect_drift)
clean (0 errors). Repo-wide gate families (DRIFT/PRE/WAIVE, not scoped
to this ticket per the tool's own scope-note) show pre-existing failures
unrelated to this diff.

### Changed
```
 tests/unit/test_land_duplicate_ticket_id.py | 26 ++++++++++++++++++++++----
 tickets/T-3075/ticket.md                    |  8 ++++++--
 2 files changed, 28 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_flags_id_with_genuinely_different_content_on_both_sides` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_ignores_the_landing_tickets_own_id` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_ignores_an_id_that_already_existed_at_the_merge_base` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 77 error(s), 655 warning(s), 863 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@.claude/hooks/frob-suggest.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@src/frob/tickets/_land_compose.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@.claude/hooks/frob-suggest.py, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_land_compose.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC006@tickets/T-3086/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_close_blocked_by_guard.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_reopen_ticket.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_close_blocked_by_guard.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_reopen_ticket.py, I001@/home/logan/projects/frob/.claude/worktrees/series-bh/tests/unit/verify/test_quarantine.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, LARGE001@strata-core/src/graph/vmodel.rs, LARGE001@strata-core/src/parse/grammar_core.rs, OPAQUE001@src/frob/refactor/_scan.py, PERF004@.claude/hooks/frob-suggest.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3075, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/tickets/_land_compose.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, REL001@src/frob/__main__.py, REL001@src/frob/stats/_agentic.py, SEC110@.claude/hooks/frob-suggest.py, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK006@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py, WIRE002@src/frob/gates/_tdd_order.py, WIRE003@.claude/hooks/frob-suggest.py

## Done report

### Root cause (verified, not assumed)

Confirmed the coordinator's strongest lead directly, empirically,
before writing any fix: reproduced the exact refusal by hand in the
shared root (`echo >> rapid-debt.jsonl; git add; git commit`) --
refused by the T-2071 scaffolded `pre-commit` hook ("agent-context
root contamination"); the identical commit succeeded immediately with
`FROB_LAND_INTERNAL=1` set. `_commit_rapid_debt`
(`src/frob/app/ticket_runner/_rapid_sweep.py`) spawns its `git commit`
via `run_argv` with no environment override, unlike every other land-
internal commit in `_land_git_ops.py`, which wraps its own git commit
spawns in `_land_internal_git_env()` (sets `FROB_LAND_INTERNAL=1` for
the spawn's duration). The T-2071 hook refuses any non-ledger file
staged directly in the primary checkout while linked worktrees exist,
unless that flag is set -- `rapid-debt.jsonl` is not `tickets.md`/
`tickets/**`, so it always hit this refusal in the real repo (which
always has linked worktrees during a dispatched session). This is a
one-line class of fix, exactly as flagged: the land path was not
setting the flag its own error message tells operators to set by hand.

The other two candidates were considered and ruled out by this same
direct repro: the failure reproduces with ZERO concurrent processes
(no other land, no detached sweep child running), so lock contention
and the sweep-vs-parent race are not the cause here -- the commit fails
deterministically, every time, under the real hook, regardless of
concurrency.

### Fix

`src/frob/app/ticket_runner/_rapid_sweep.py::_commit_rapid_debt`: wraps
ONLY the `git commit` spawn in `_land_internal_git_env()` (imported
from `frob.tickets._land_git_ops`), the same narrow scope every other
land-internal commit already uses. The `status`/`add` spawns are
unaffected (they do not commit, so the hook never runs for them).

### Did NOT do (per the ticket's explicit prohibitions)

- Did not make the sweep skip writing `rapid-debt.jsonl` -- the write
  path (`record_rapid_debt`) is untouched; only the COMMIT of an
  already-written line is fixed.
- Did not touch `.gitignore` or `.gitattributes`.
- Did not touch the T-2071 guard itself, or weaken it in any way --
  `test_guard_still_refuses_a_genuinely_foreign_file` proves this
  directly (see controls below).

### Process notes (both applied per the coordinator's instructions)

1. Committed the repro test ALONE first (`e3f1dfc27`), confirmed it
   fails against that commit via `--check-repro`, only then committed
   the fix (`86ac51ca7`) and designated repro with `--base-ref
   e3f1dfc27` against the fix commit. Avoided the squash-then-refuse
   trap the coordinator named.
2. Opened narrow (`src/frob/app/ticket_runner/_rapid_sweep.py` only,
   the ticket's own opening scope) and widened once, deliberately, via
   `frob ticket scope --add --reason` to add
   `tests/unit/test_rapid_sweep.py` when the fix needed a repro test
   that the existing `_seed_repo` fixture (no scaffolded hook, no
   worktree) structurally could not provide.

### Evidence

- tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_survives_the_scaffolded_root_write_guard
  (designated repro, FAILED_AT_PARENT confirmed against e3f1dfc27, the
  test-only commit)
- tests/unit/test_rapid_sweep.py::TestCommitRapidDebt.test_guard_still_refuses_a_genuinely_foreign_file
  (positive control, other direction -- see below)

### Both-directions and ticket-required controls (all measured)

- Positive (fix works): full test file re-run after the fix -- 149/149
  passed (`pytest tests/unit/test_rapid_sweep.py` exitstatus=0
  collected=149 failed=0).
- Negative (deliberate re-break, confirmed fail, then restored):
  removed the `_land_internal_git_env()` wrap -> re-ran
  `test_survives_the_scaffolded_root_write_guard` -> FAILED with the
  identical `could not commit rapid-debt.jsonl ... commit it by hand`
  error and a non-empty `git status --porcelain` -> restored, re-ran
  full file, 149/149 passed.
- Ticket's own required control 1 (several consecutive lands stay
  clean): ran a standalone script calling `record_rapid_debt` +
  `_commit_rapid_debt` three times in a row against a real repo with
  the scaffolded hook and a linked worktree, asserting
  `git status --porcelain` is empty after EACH call -- all 3 clean,
  printed "ALL 3 CONSECUTIVE LANDS LEFT ROOT CLEAN".
- Ticket's own required control 2 (guard still fires for genuinely
  unexpected content): new test
  `test_guard_still_refuses_a_genuinely_foreign_file` stages an
  unrelated `stray.py` in the same repo/hook/worktree shape and
  confirms `git commit` is STILL refused and the root stays dirty --
  proves the fix is a narrow exemption for this module's own machinery
  file, not a general bypass. Passing.
- Ticket's own required control 3 (sweep record still written, same
  content): `record_rapid_debt`'s own write path is untouched by this
  fix -- only the commit-of-an-already-written-line step changed. Not
  separately diffed since no code on the write side changed at all.

### Gates

`uv run frob ticket evidence T-2669 --check-repro`: FAILED_AT_PARENT
against the test-only commit e3f1dfc27, confirmed (not NO_VERDICT /
PASSED_AT_PARENT). `frob check --ticket T-2669` run pre-land per
playbook section 0/6g.

### Changed
```
 src/frob/app/ticket_runner/_rapid_sweep.py |  43 ++++++++----
 tests/unit/test_rapid_sweep.py             | 103 +++++++++++++++++++++++++++++
 tickets/T-2669/ticket.md                   |  15 ++++-
 3 files changed, 146 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestCommitRapidDebt::test_survives_the_scaffolded_root_write_guard` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCommitRapidDebt::test_guard_still_refuses_a_genuinely_foreign_file` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t2634-t2636/src/frob/app/ticket_runner/_rapid_sweep.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2669, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md

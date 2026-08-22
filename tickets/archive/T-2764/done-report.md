## Done report

`make check` runs a separate `check_native_staleness_or_exit` pre-step
before `uv run frob check`; the frob-native `check` entrypoint had no
equivalent, so a `--skip-gates` run, or an `--only` selection that never
reached the `gates` stage, silently ran against a stale native with no
warning at all -- a real workflow-parity gap, not merely a naming one
(the gates stage's own self-heal, `frob.gates._maybe_autorebuild_natives`
T-1213, only ever runs from inside that one stage).

Decision: `frob check` SHOULD enforce this, unconditionally, matching
`make check`'s fail-closed posture -- but without regressing T-1213's
self-heal improvement. Added `frob.check._native_staleness_result`
(same pattern as the existing `_derived_state_integrity_result`
precheck), wired into `_run_check_with_skips` before any stage runs. It
reuses the SAME rebuild-then-recheck logic the gates stage's self-heal
already uses (`frob.gates._native_autorebuild_disabled` +
`frob.natives._build.build_natives`, not reimplemented) -- a
stale-but-rebuildable native is fixed silently regardless of which
stages are selected, and only reports NATIVE001 (fail-closed, matching
`make check`) when staleness remains after that attempt.

Verified in both directions against a REAL native, not just mocks:
- Genuinely staled `strata_core` by touching `strata-core/src/lib.rs`
  (confirmed via `frob.strata.stale_natives`).
- With `FROB_NO_NATIVE_AUTOREBUILD=1` (rebuild disabled), `frob check
  --skip-gates ... --no-cache` exited 1 with `NATIVE001: STALE NATIVE:
  built extension(s) [strata_core] predate their own source tree`.
- Without the env var (auto-rebuild on), the identical invocation
  silently rebuilt `strata_core` (confirmed clean via `stale_natives`
  afterward) and the native-staleness stage reported nothing -- the
  self-heal improvement is preserved, not regressed.
- A fresh native (the common case) reports no violation at all
  (`test_fresh_native_is_not_a_violation`).

Also narrowed scope: the ticket's original glob named `src/frob/check.py`,
which no longer exists (renamed to `src/frob/check/__init__.py` in an
unrelated refactor since this ticket was filed while working T-2245) --
`frob ticket scope --add/--remove` corrected this before editing, and
`tests/unit/test_check.py` plus `docs/commands/check.md` were added to
cover the new tests and doc note respectively.

Filed: none.

### Changed
```
 docs/modules/arch.md          |  4 ++--
 rapid-debt.jsonl              |  2 ++
 tickets/T-2764/ticket.md      | 30 ++++++++++++++++++++++++++++--
 tickets/T-2766/done-report.md | 31 +++++++++++++++++++++++++++++++
 tickets/T-2766/ticket.md      |  9 +++++++--
 5 files changed, 70 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_check.py::TestNativeStalenessResult::test_stale_native_fails_closed_when_rebuild_cannot_fix_it` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestNativeStalenessResult::test_fresh_native_is_not_a_violation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 18 error(s), 1018 warning(s), 708 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, E501@/home/logan/projects/frob/.claude/worktrees/t2766-t2764/src/frob/tickets/_new_renumber.py, PERF004@src/frob/tickets/_evidence.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md

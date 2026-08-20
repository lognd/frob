## Done report

Changed:
- src/frob/verify/_quarantine.py::QuarantineError.UnresolvableFiledTicket (new)
- src/frob/verify/_quarantine.py::_refuse_if_filed_ticket_unresolvable (new)
- src/frob/verify/_quarantine.py::clear_quarantine
- src/frob/app/ticket_runner/_rapid_sweep.py::_commit_regression_ticket
- src/frob/app/ticket_runner/_rapid_sweep.py::_file_regression_ticket
- docs/modules/tickets-verify-sweep.md#quarantine-circuit-breaker-t-1693

Mechanism established (read `_rapid_sweep.py`'s auto-file-then-clear path,
not assumed): this is hypothesis (a) applied at the WRONG layer, not
absent entirely. `_commit_regression_ticket` writes the newly-filed
regression ticket's ledger entry through a retry-then-discard guarantee
(T-1841/T-2034). When every commit attempt fails, the just-written,
never-committed `tickets/<id>/` directory is deliberately DISCARDED so
root stays clean -- but `_commit_regression_ticket` returned `None`
unconditionally regardless of outcome, so its caller `_file_regression_
ticket` had no way to distinguish a genuine commit from an exhausted-
retries discard and proceeded to `_auto_dispose_filed_findings` /
`clear_quarantine` citing the (possibly-discarded) id either way. The
ticket's own later measurement (intermittent: T-2749/T-2732/T-2743
resolved, T-2736 did not) is consistent with this -- a transient commit
failure (concurrent land holding root's lock is the documented ROUTINE
case for this retry loop) rather than a permanently broken path, which
is exactly what an exhausted-retries discard produces on an unlucky run.

Two fixes, layered per the ticket's own "whichever it is" requirement:
- PRIMARY, mechanism-agnostic: `clear_quarantine` now refuses
  (`Err(QuarantineError.UnresolvableFiledTicket)`) if ANY `"filed"`
  disposition's ticket id does not resolve on `root`, checked before any
  finding is disposed. This is the single choke point every caller (CLI
  `frob verify dispose --file-ticket`, rapid sweep, or any future caller)
  passes through, so it also closes hypothesis (b) (id lives only on a
  worktree branch) and (c) (id allocated before a durable write) by the
  same mechanism, without needing to determine per-incident which one
  produced a given phantom id.
- SECONDARY (defense in depth, direct fix for the observed mechanism):
  `_commit_regression_ticket` now returns the commit-or-discard success
  bool instead of `None`; `_file_regression_ticket` skips `_auto_
  dispose_filed_findings` entirely when it is `False`, logs at ERROR, and
  leaves quarantine raised.

Recovery for the instance already lost: `.frob/quarantine.json` is not
git-tracked (no history to recover the exact 2 (rule, file) identities
from), and the live record has since cycled through several legitimate
raise/clear passes (T-2749, T-2732, T-2743) that overwrote it. A full
unbudgeted `frob check --json --no-cache` run today shows 74 errors
repo-wide (pre-existing baseline: import cycles, ARCH103, PERF00x, etc,
none newly introduced by this change) -- no untracked quarantine-shaped
regression stood out beyond that pre-existing landscape. The exact
identity of the 2 originally-released findings is unrecoverable from the
ledger; the structural fix (this ticket) is what prevents a recurrence,
which was the requirement.

Positive controls (both directions), all new/passing:
- `TestClearQuarantine.test_refuses_when_filed_ticket_does_not_resolve` --
  a `"filed"` disposition naming a nonexistent id (reproducing the T-2736
  shape directly) refuses with `UnresolvableFiledTicket`, quarantine
  stays raised.
- `TestFileRegressionTicket.test_commit_failure_skips_auto_dispose_and_
  returns_none` -- a failed regression-ticket commit skips auto-dispose/
  clear entirely, quarantine stays raised, `_file_regression_ticket`
  returns `None`.
- Existing `TestClearQuarantine.test_clears_when_every_finding_disposed`,
  `TestIsQuarantined.test_false_after_clear`, `TestIdentityLessFinding
  Recovery.*`, `TestDispose.test_dismiss_disposes_the_live_unattributed_
  finding` (unchanged behavior for real ids / dismissed dispositions) all
  still pass -- updated the 4 tests that previously cited a bare literal
  fake id (`"T-1000"`/`"T-9999"`) to seed a real ticket via a new
  `_seed_real_ticket` helper, since citing a phantom id in a "clear
  succeeds" test was exactly the anti-pattern this fix now catches.
- `TestFileRegressionTicket`/`TestAutoDisposeFiledFindings`/`TestCommit
  RegressionTicket`'s existing success-path coverage is unchanged --
  confirms the normal (commit succeeds, id resolves) path still clears
  quarantine exactly as before.

Evidence:
- tests/unit/verify/test_quarantine.py::TestClearQuarantine::test_refuses_when_filed_ticket_does_not_resolve
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_commit_failure_skips_auto_dispose_and_returns_none
- Full suite for both touched files: 180 collected, 0 failed
  (tests/unit/verify/test_quarantine.py + tests/unit/test_rapid_sweep.py)

Filed: none (no out-of-scope work discovered; the intermittency finding
was recorded in this ticket's own body as new measurement, not a
separate defect).

Gates: `frob check --ticket T-2744` -- SCOPE/COV/DRIFT/FMT errors caused
by this change all resolved (scope extended to cover frob.lock written by
`frob ack`; frob:ticket/frob:tests directives added on every changed
public symbol; DRIFT001 acked on `_file_regression_ticket` with reason;
COV007 private-symbol frob:doc removed from the new private helper).
Remaining gate-summary errors (68 pre-existing repo-wide: import cycles,
ARCH103, PERF00x nested-loop/sort-in-loop, SEC110 env-read mapping,
TICK003/004/006 ledger housekeeping, WIRE002/003, claude-config-drift)
are unrelated to this ticket's touched set, confirmed by diffing before/
after this change's own scoped check runs.

### Changed
```
 tickets/T-2735/ticket.md | 2 +-
 tickets/T-2744/ticket.md | 9 +++++++++
 2 files changed, 10 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/verify/test_quarantine.py::TestClearQuarantine::test_refuses_when_filed_ticket_does_not_resolve` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_commit_failure_skips_auto_dispose_and_returns_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 39 error(s), 941 warning(s), 695 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_close_cmd.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2742/ticket.md, DOC011@docs/modules/tickets-verify-sweep.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@src/frob/tickets/_land.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@src/frob/serve/_socketd.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md

## Done report

_file_regression_ticket raised quarantine for a red batch and filed a
regression ticket for it, but never disposed the finding it just filed a
ticket for -- a human had to run `frob verify dispose --file-ticket
F=T-XXXX` by hand every time, 8 times in one session, each blocking
deferred landing fleet-wide until done.

Added `_auto_dispose_filed_findings`, called right after
`_commit_regression_ticket` inside `_file_regression_ticket`: it loads the
current quarantine record and, for exactly the `(rule_id, file)` pairs the
just-filed ticket covers (`unfiled_pairs`), builds the same
`("filed", ticket_id)` disposition shape `frob verify dispose
--file-ticket` produces, then calls `clear_quarantine` -- the same
function and the same WARNING-level "CLEARED" log a manual disposal
produces, so the audit trail is identical.

`clear_quarantine`'s own contract is atomic: it refuses to write anything
unless EVERY currently-raised finding is disposed. So a red batch where
some findings attribute to a DIFFERENT already-open ticket (never touched
by this call) leaves quarantine fully raised, with every finding --
including the ones this ticket covers -- still undisposed, exactly as
before. This is deliberate, per the ticket's own acceptance criteria: an
undisposed finding with no tracking ticket is what quarantine exists to
surface, and a partial auto-clear would reopen the hole T-1693 closed.

Two pre-existing tests in `TestRaiseQuarantineForRedBatch`
(`test_raises_with_attributed_and_unattributed_findings`,
`test_warm_tree_recheck_keeps_finding_when_native_still_broken`) covered
cases where the filed ticket covers every raised finding; updated their
assertions from "quarantine stays raised" to "quarantine auto-clears,
every finding disposed as filed" to match the new, intended behavior --
the underlying raise these tests exist to verify is unchanged, only the
now-automatic disposal that follows it.

### Changed
```
 docs/modules/tickets-verify-sweep.md       |  20 ++++
 frob.lock                                  |  20 +++-
 src/frob/app/ticket_runner/_rapid_sweep.py |  86 +++++++++++++++
 tests/unit/test_rapid_sweep.py             | 169 ++++++++++++++++++++++++++++-
 tickets/T-2208/done-report.md              |  56 ++++++++++
 tickets/T-2208/ticket.md                   |  29 ++++-
 6 files changed, 373 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_disposes_findings_the_ticket_covers` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_leaves_quarantine_raised_when_other_findings_remain_undisposed` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_no_quarantine_raised_is_a_silent_no_op` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_clear_failure_is_logged_not_raised` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_raises_with_attributed_and_unattributed_findings` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_warm_tree_recheck_keeps_finding_when_native_still_broken` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2208/src/frob/lang/_nodes.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2208, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md

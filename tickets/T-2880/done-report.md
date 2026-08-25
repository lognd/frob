## Done report

T-2849's `arm_parent_death_signal` closes the PDEATHSIG race between
"read my current parent" and "the arm call actually takes effect" by
comparing `os.getppid()` before vs. after the `prctl` call and self-
killing on a diff. That comparison is blind to a parent that already
died BEFORE the function was ever entered: `fork()` returns in the
child, the real parent dies, and only THEN does the child get around to
calling `arm_parent_death_signal` -- by the time `parent_before` is
read, the kernel has already reparented the caller to init (pid 1), so
both the before and after reads agree on the same (already-wrong)
answer and the diff check finds nothing to flag. The process then arms
`PR_SET_PDEATHSIG` against a parent (init) that will never die, so the
signal never fires, and the process leaks exactly as it did before
T-2849 landed. This matches the measured shape from the ticket body:
T-2849's fix is loaded and its own isolated controls pass (fresh
process, fresh helper, env set first, no time for the race to open),
but a real `frob check` run -- more surface area, more chances for a
parent to die between fork and arm -- kept producing new orphans at
roughly the pre-fix rate.

Fix: `arm_parent_death_signal` (src/frob/process/_reap.py) now also
checks, after the diff check, whether the CURRENT parent is pid 1
outright, not only whether it changed during the call. Neither a
forkserver helper's real parent (the `frob check` launcher) nor a
worker's real parent (the helper) is ever legitimately pid 1 in this
codebase's process tree -- no subreaper is installed anywhere (grepped)
-- so `getppid() == 1` at this point is unambiguous evidence that the
real parent is already gone, whether that happened during this call or
before it was even entered. Self-deliver the signal in that case too.
T-2849's mechanism and both its use sites (`_open_process_pool`'s
helper-arm stamp, the pool's worker `initializer`) are unchanged -- this
only hardens the one shared primitive both use.

## Done report

Changed:
- src/frob/process/_reap.py::arm_parent_death_signal
- tests/unit/test_process_reap.py::TestArmParentDeathSignal.test_self_kills_when_already_reparented_before_entry
- docs/modules/process.md#forkserver-reaping-t-2443

Evidence: tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_self_kills_when_already_reparented_before_entry
(designated repro, FAILED_AT_PARENT at 4afdde7b0 -- verified with
`frob ticket evidence --check-repro`); full
tests/unit/test_process_reap.py (27 tests) and `frob test --base main`
touched-set both pass.

Filed: none -- T-2884 (daemon version-skew self-heal) was already filed
by a prior attempt on this ticket and remains open, tracked separately;
no new follow-up work was cut from this ticket's scope.

Gates: `frob check --ticket T-2880 --no-cache` clean for this ticket's
own scope/diff (AFFECT001, COV002, SCOPE001, PRE001 all resolved); every
remaining FAIL line in the repo-wide summary is pre-existing on main,
outside this ticket's scope (confirmed via `git show main:...` for the
DOC006 ticket-body pointer, and by symbol for the COV004/COV006/
TICK004/TICK006 findings -- none touch `frob.process._reap` or this
ticket's files).

### Changed
```
 docs/modules/process.md         | 20 ++++++++++
 src/frob/process/_reap.py       | 47 +++++++++++++++++++++-
 tests/unit/test_process_reap.py | 27 +++++++++++++
 tickets/T-2880/done-report.md   | 87 +++++++++++++++++++++++++++++++++++++++++
 tickets/T-2880/ticket.md        | 36 +++++++++++++++--
 5 files changed, 212 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_process_reap.py::TestArmParentDeathSignal::test_self_kills_when_already_reparented_before_entry` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 18 error(s), 476 warning(s), 846 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@tickets/T-2880/ticket.md, DOC006@tickets/T-2884/ticket.md, DOC006@tickets/T-2886/ticket.md, TICK004@tickets.md, TICK006@tickets.md

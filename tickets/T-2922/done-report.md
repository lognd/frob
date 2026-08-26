## Done report

Changed:
- src/frob/gates/_fix_engine.py -- removed the "SYS100" entry and
  `_fix_sys100_both_cases` wrapper from TIER_A_HANDLERS; import of
  fix_sys100_may_via_union/fix_sys100_extended_whole_node_grant dropped.
- src/frob/gates/_fix_engine_sync.py -- deleted
  fix_sys100_may_via_union (T-1531) and fix_sys100_extended_whole_node_grant
  (T-1545) outright; replaced with a "SYS100 auto-widening -- REMOVED"
  comment block recording the T-1623/T-1628 supersession and why
  frob.strata._sync_may's writer functions are left in place for now.
  Updated the fix_sys111_capability_ratchet_sync docstring and the
  surrounding SYS111 comment block, which depended on SYS100 having
  already widened the tree this same pass.
- docs/modules/gates.md -- rewrote the SYS100 auto-fix section to
  document the removal, the ceiling-vs-observed-behavior rationale, and
  the T-1623/T-1628 supersession; corrected the SYS111 paragraph's
  stale cross-references.
- tests/test_gates.py -- replaced the four T-1531/T-1545 acceptance
  tests (which asserted the auto-widening APPLIED) with a must-still-fire
  / must-not-auto-resolve proof pair, and fixed the completeness test
  (test_tier_a_handlers_dict_covers_every_batch_rule) to drop "SYS100"
  from TIER_A_HANDLERS' expected key set.

Proof (both directions):
- must-still-fire: test_sys100_core_violation_still_fires_and_is_not_auto_resolved
  and test_sys100_extended_violation_still_fires_and_is_not_auto_resolved
  assert sys_gate's production entrypoint still folds an unwaived SYS100
  finding into SELFAUDIT001 both BEFORE and AFTER a Tier-A fix pass.
- must-not-auto-resolve: the same two tests assert apply_tier_a_fixes
  produces zero SYS100 FixApplied entries and leaves the .strata design
  file byte-for-byte unchanged.
- Repro: designated
  tests/test_gates.py::TestFixEngineTierA::test_sys100_core_violation_still_fires_and_is_not_auto_resolved
  as this ticket's BUG002 repro, base-ref 25aedc832 (a commit containing
  the test with the still-buggy SYS100 auto-widener in place) --
  `frob ticket evidence --check-repro` confirmed FAILED_AT_PARENT.

Evidence:
- tests/test_gates.py::TestFixEngineTierA::test_sys100_core_violation_still_fires_and_is_not_auto_resolved
  (designated repro)
- tests/test_gates.py::TestFixEngineTierA::test_sys100_extended_violation_still_fires_and_is_not_auto_resolved
- tests/test_gates.py::TestFixEngineTierABatch2::test_tier_a_handlers_dict_covers_every_batch_rule

Gates: `uv run frob check --only test --ticket T-2922` clean (0 errors,
53 warnings, 5 waived, all pre-existing). `--only refs --only docanchor
--only doclink --ticket T-2922` shows one pre-existing DOC008 (a broken
link in docs/commands/check.md unrelated to this change, confirmed
failing identically on main before this ticket's commits) plus the
standing CLAUDE001 config-drift note; no new findings from this ticket's
own diff. `tests/test_gates.py -k TestFixEngineTierA` full-class run:
only the pre-existing, unrelated
test_docenum001_fails_before_fix_and_passes_after failure remains
(confirmed failing identically on main before this ticket touched
anything).

Historical note (per dispatch instructions): _sync_may.py's own
docstring (T-1531, cited from _fix_engine_sync.py's now-deleted SYS100
comment block) attributed the auto-widening policy to T-1623/T-1628 --
a deliberate decision at the time. T-2922/T-2920 supersede that decision
on the user's explicit instruction: a `may=` list is meant to be a
ceiling a human controls, not a mirror of whatever the code already
does.

Filed: none -- both known follow-ups (deleting frob.strata._sync_may's
now-dead writer functions once T-2920 lands, and T-2928's own detector
work) are already tracked by name in this dispatch, not new discoveries.

Coordination note: stayed entirely out of src/frob/strata/** and
design/** per the T-2920 concurrency instruction. _sync_may.py's writer
functions (apply_sync_may, sync_may_report, apply_sync_may_extended,
sync_may_extended_report, WholeNodeMayGrantDiff) are now dead code but
deliberately left in place; deleting them is this ticket's own
documented follow-up commit once T-2920's own use of that file is
confirmed clear.

### Changed
```
 docs/modules/gates.md              | 144 +++++++++++--------------
 src/frob/gates/_fix_engine.py      |  49 +++++----
 src/frob/gates/_fix_engine_sync.py | 216 +++++++++++++++----------------------
 tests/test_gates.py                | 156 +++++++++++++++------------
 tickets/T-2922/done-report.md      |  95 ++++++++++++++++
 tickets/T-2922/ticket.md           |  47 +++++++-
 tickets/archive/T-1531/ticket.md   | 183 +++++++++++--------------------
 tickets/archive/T-1545/ticket.md   |  70 +++++++++++-
 tickets/archive/T-1924/ticket.md   | 122 ++++++++++++++++++++-
 9 files changed, 652 insertions(+), 430 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierA::test_sys100_core_violation_still_fires_and_is_not_auto_resolved` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys100_extended_violation_still_fires_and_is_not_auto_resolved` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_tier_a_handlers_dict_covers_every_batch_rule` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 19 error(s), 1550 warning(s), 850 waived
- error-findings: COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, PRE001@tickets/T-2922, TICK004@tickets.md, WIRE002@src/frob/tickets/_unlanded.py

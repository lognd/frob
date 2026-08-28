## Done report

Changed:
- src/frob/strata/_sync_may.py: deleted sync_may_report/apply_sync_may/
  sync_may_extended_report/apply_sync_may_extended/WholeNodeMayGrantDiff
  and their private helpers -- confirmed zero remaining importers
  repo-wide (git grep verified) once T-2922 unwired the only caller.
  Kept _NODE_HEADER_RE/node_body_span (frob.strata._shrink's genuine,
  live import) and rewrote the module docstring/__all__ to describe the
  narrower remaining purpose.
- tests/unit/strata/test_sync_may.py: deleted the matching dead test
  classes (TestSyncMayReport/TestApplySyncMay/
  TestSyncMayExtendedReport/TestApplySyncMayExtended); kept
  TestNodeBodySpan.
- tests/unit/strata/test_shrink.py: added TestNoWideningPathRepoWide,
  extending T-2923's own explicitly-scoped TestNoWideningPath (which
  disclosed it could not yet prove the epic-wide property, since the
  widening functions still existed) to a real repo-wide AST walk over
  every .py file under src/frob confirming none defines or imports one
  of the five deleted widening symbols.
- src/frob/gates/_fix_engine.py, _fix_engine_sync.py: updated the
  T-2922-authored comments that predicted this exact follow-up deletion
  ("left in place for now... follow-up commit") to stop describing it
  as pending.
- Repaired three archived tickets' (T-1531, T-1545, T-1857) now-stale
  evidence citing the deleted tests via `frob ticket evidence --replace
  --archived` (same recipe used for T-1531/T-1545/T-1924 under T-2922).

Free controlled-deletion measurement (per the coordinator's request,
added to the miss-set catalog T-2928 already documents): BEFORE
deleting, ran the full gate suite against the still-live, but already-
uncalled, widening functions. Zero findings from ANY detector --
WIRE001 (diff-scoped, cannot see pre-existing code), REF001/REF002
(file-granularity: _sync_may.py has a real consumer via node_body_span,
so the file clears the pass bar), AND DEAD001 (private-symbol-only by
design -- these five functions are PUBLIC, in __all__, so DEAD001 does
not even attempt to evaluate them). This is a THIRD distinct miss
shape beyond T-2928's own two: a fully public function with zero
callers is invisible to every detector in this repo, not just the two
T-2928 already named. Recorded here since T-2928 itself is already
closed; a future reader auditing dead-code coverage should read both
Done reports together.

Epic-level re-verification (T-2920's acceptance criteria, measured
fresh in this worktree, not assumed from the epic's own briefing):
- shrink-only auto-tightening: `frob sys shrink --check .` on frob's
  own repo reports "no SYS101 findings" / "nothing to tighten" -- live,
  confirmed working (T-2923).
- capability escalation always an ERROR, never auto-synced: SYS100 has
  no Tier-A handler (T-2922); TestFixEngineTierA's must-still-fire/
  must-not-auto-resolve pair still passes.
- unbound capability-bearing file stays an ERROR: SYS103,
  TestShrinkNeverWidensOrBinds::
  test_unbound_capability_file_stays_an_error_and_shrink_does_not_bind_it
  still passes.
- must-not-regress (no flag/env/config enables auto-widening): NOW
  provable at the real repo-wide scope (TestNoWideningPathRepoWide,
  this ticket) -- T-2923's own Done report explicitly disclosed this
  could not be claimed yet; it can now.
- must-still-pass control: `frob sys audit .` on frob's own repo --
  9 total gaps, 2 self-conformance (both SYS107, pre-existing,
  testsuite's via-less fs.read/fs.write over the 20-file threshold,
  unrelated to any of this program's tickets), UNCHANGED before and
  after this ticket's diff. CORRECTION preserved from T-2923's own Done
  report and re-confirmed here: frob's own repo does NOT hold "0 SYS
  errors" (the epic body's own assumption) -- it holds 2, unchanged.
  Using the measured number, not the epic's prose.

EPIC STATUS: T-2920 (tier=epic) CANNOT close yet. Its own
`no_scope_declared_reason` names four implementation pieces: frob sys
shrink (T-2923, done), escalation-is-error enforcement (T-2922, done),
frob sys init (T-2910), and this widening-unwire-and-cleanup work
(T-2922 + this ticket, done). Checking `parent: T-2920` across the
active ledger directly (not assumed from the coordinator's briefing,
which did not mention either) found TWO further children: T-2910
(frob sys init, state: queued at investigation time, a land for it was
observed in flight during this ticket's own work) and T-2911 (frob
status: show movement, state: in-progress) -- both still open. The
epic's own 5 acceptance-criteria bullets are now fully satisfied and
re-verified by this ticket, but the epic cannot be marked done while
two of its own named/tracked children remain non-terminal. No new
decomposition is needed -- both children already exist as tracked leaf
tickets; T-2920 should stay open until they close.

Evidence:
- tests/unit/strata/test_sync_may.py::TestNodeBodySpan::test_flat_body_returns_closing_brace_line
- tests/unit/strata/test_sync_may.py::TestNodeBodySpan::test_nested_braces_do_not_close_early
- tests/unit/strata/test_shrink.py::TestNoWideningPathRepoWide::test_widening_functions_no_longer_exist_in_sync_may
- tests/unit/strata/test_shrink.py::TestNoWideningPathRepoWide::test_no_module_under_src_frob_defines_or_imports_a_widening_function

Filed: none new -- T-2910/T-2911 already exist and are already tracked
under T-2920; no further decomposition needed.

Gates: `frob check --only test --ticket T-2935` -- 1 pre-existing error
(TEST001 on scripts/branch_stranded_work_analysis.py, confirmed
untouched by this ticket, repo-wide baseline). `--only coverage
--ticket T-2935` -- zero sync_may-related findings after the evidence
repair above. `frob sys audit .` and `frob sys shrink --check .` both
re-run fresh in this worktree per the coordinator's explicit
"re-verify, do not assume" instruction.

### Changed
```
 src/frob/gates/_fix_engine.py      |  20 +-
 src/frob/gates/_fix_engine_sync.py |  14 +-
 src/frob/strata/_sync_may.py       | 750 ++-----------------------------------
 tests/unit/strata/test_shrink.py   |  86 +++++
 tests/unit/strata/test_sync_may.py | 276 +-------------
 tickets/T-2935/done-report.md      | 122 ++++++
 tickets/T-2935/ticket.md           |   9 +-
 tickets/archive/T-1531/ticket.md   | 196 +++++++++-
 tickets/archive/T-1545/ticket.md   | 112 +++++-
 tickets/archive/T-1857/ticket.md   |  94 ++++-
 10 files changed, 670 insertions(+), 1009 deletions(-)
```

### Evidence
- `tests/unit/strata/test_sync_may.py::TestNodeBodySpan::test_flat_body_returns_closing_brace_line` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_sync_may.py::TestNodeBodySpan::test_nested_braces_do_not_close_early` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shrink.py::TestNoWideningPathRepoWide::test_widening_functions_no_longer_exist_in_sync_may` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shrink.py::TestNoWideningPathRepoWide::test_no_module_under_src_frob_defines_or_imports_a_widening_function` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 21 error(s), 561 warning(s), 849 waived
- error-findings: COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md

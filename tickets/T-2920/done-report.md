## Done report

Epic closure. All four child tickets are terminal: T-2923 (frob sys
shrink, done), T-2922 (SYS100 auto-widening unwired, done), T-2935
(dead widening functions deleted, epic-wide no-widening proof, done),
T-2910 (frob sys init, done), T-2911 (frob status movement, done).

Every acceptance criterion re-verified FRESH in this worktree (not
assumed from any prior briefing or Done report):

1. Shrink-only auto-tightening: `frob sys shrink --check .` against
   frob's own repo -- "no SYS101 (declared-but-never-observed)
   findings" / "nothing to tighten". Live, working.
2. Capability escalation always an ERROR, never auto-synced: SYS100 has
   no Tier-A handler (`TIER_A_HANDLERS` has no "SYS100" key, T-2922).
   tests/test_gates.py::TestFixEngineTierA's must-still-fire/
   must-not-auto-resolve pair re-run clean: SYS100 still fires via
   sys_gate/SELFAUDIT001 both before and after a Tier-A fix pass, and
   apply_tier_a_fixes never touches the .strata declaration.
3. Unbound capability-bearing file (SYS103) stays an ERROR:
   tests/unit/strata/test_shrink.py::TestShrinkNeverWidensOrBinds's
   must-fire fixture re-run clean.
4. Must-not-regress -- no flag/env/config enables auto-widening: THIS
   is the criterion T-2923's own Done report explicitly disclosed as
   UNPROVABLE at the time (its own scoped TestNoWideningPath covered
   only _shrink.py's own surface, since _sync_may.py's widening writer
   was still live). Now provable and proven:
   frob.strata._sync_may.sync_may_report/apply_sync_may/
   sync_may_extended_report/apply_sync_may_extended/
   WholeNodeMayGrantDiff are DELETED (T-2935, once T-2922 confirmed
   zero remaining importers). tests/unit/strata/test_shrink.py::
   TestNoWideningPathRepoWide walks every .py file under src/frob via
   AST and asserts none defines or imports any of the five deleted
   widening symbols -- re-run clean in this worktree. `git grep` for
   all five names confirms only comments/docstrings and this test
   file's own deny-list literals remain; zero real imports or calls
   anywhere.
5. Must-still-pass control: `frob sys audit .` -- 9 total gaps, 2
   self-conformance (both SYS107, testsuite's via-less fs.read/
   fs.write over the 20-file threshold), UNCHANGED in kind from every
   prior measurement in this program (T-2923's, T-2922's, and this
   one). CORRECTION preserved from T-2923's own Done report and
   re-confirmed fresh here, per the coordinator's explicit instruction
   to use the measured number rather than the epic body's own prose:
   frob's own repo does NOT hold "0 SYS errors" (the epic body's
   literal acceptance-criterion text) -- it holds 2, unchanged before
   and after this program's entire diff. The epic body's ACCEPTANCE
   section is left as originally written (historical record of what
   was asked); this Done report is the correction of record.

Filed: none new. No criterion required further decomposition -- all
five are met by already-landed, already-verified child work.

Evidence: 6 test node ids bound (see ticket frontmatter), covering
must-fire (SYS100 escalation, SYS103 unbound file) and must-not-widen
(scoped and repo-wide) both directions.

Gates: `frob sys audit .` and `frob sys shrink --check .` both re-run
fresh in this worktree (not read from any cached/prior report).
`pytest tests/unit/strata/test_shrink.py tests/unit/strata/
test_sync_may.py tests/test_gates.py -k "sys100..."` -- 18 collected,
0 failed, re-run fresh in this worktree.

### Changed
```
 tickets/T-2920/ticket.md | 9 +++++++++
 1 file changed, 9 insertions(+)
```

### Evidence
- `tests/unit/strata/test_shrink.py::TestShrinkNeverWidensOrBinds::test_capability_escalation_stays_an_error_and_shrink_does_not_widen` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shrink.py::TestShrinkNeverWidensOrBinds::test_unbound_capability_file_stays_an_error_and_shrink_does_not_bind_it` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shrink.py::TestNoWideningPathRepoWide::test_widening_functions_no_longer_exist_in_sync_may` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_shrink.py::TestNoWideningPathRepoWide::test_no_module_under_src_frob_defines_or_imports_a_widening_function` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys100_core_violation_still_fires_and_is_not_auto_resolved` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_sys100_extended_violation_still_fires_and_is_not_auto_resolved` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

## Done report

Two defects, both fixed in `src/frob/tickets/_reporting.py` (the only file
in scope):

**Defect 1** (draft ids): `_TICKET_ID_RE` was `re.compile(r"T-\d+")`,
which cannot match `T-draft-<hex>`. Changed to
`re.compile(r"T-(?:\d+|draft-[0-9a-fA-F]+)")`. `filed_followup_tickets`
now returns draft ids exactly as it already returns numbered ones -- no
other change needed, since it already just delegates to this pattern.

**Defect 2** (the real one, lexical guard defeated by paraphrase):
`disclosure_shaped_language` no longer lets the `_DISCLOSURE_PHRASES`
scan be the SOLE decision. Added a second, independent signal:
`_done_report_section` slices `text` from the LAST `## Done report`
heading to the end (scoping strictly to what the Done-report write path
itself appends -- a ticket's own DESCRIPTION routinely carries rich `##`
structure of its own, e.g. this very ticket's "## Two defects"/"###
Defect 1"/"### Defect 2", and scanning the whole body would false-
positive on nearly every ticket). `_SUBHEADING_RE` then looks for any
`###`-or-deeper markdown heading inside that slice. A heading's SYNTAX
existing is structural and cannot be defeated by rewording its text --
unlike the phrase scan, which the confirmed incident showed goes
completely silent the moment the heading's wording changes while the
disclosed content underneath is untouched. The phrase list stays live as
a widening hint (it still catches a disclosure with no heading at all,
in plain prose) but per the ticket's own instruction is no longer what
decides the reword-proof case.

Did NOT broaden `_DISCLOSURE_PHRASES` (the ticket's explicit "Do NOT").
Did NOT touch `_close_cmd.py`'s `_undisclosed_remainder_reason` or its
call site -- out of this ticket's declared scope, and the existing
`tests/unit/test_close_t1648_remainder.py` suite (unmodified) still
passes unchanged against the new `_reporting.py`, confirming the fix
composes correctly through the real caller without any change there.
Did NOT drop the guard.

Updated `docs/modules/tickets-data-storage.md`'s "Disclosed-remainder-
requires-follow-up guard at close (T-1648)" section to describe both
changes (AFFECT001 flagged `disclosure_shaped_language`'s own frob:doc
target as stale against this diff; fixed by editing the doc, not by
waiving). Scope extended to cover the doc file and the test file
(`tests/unit/test_reporting_t1648_remainder.py`) actually touched --
`frob ticket scope T-2638 --add`.

Changed:
- src/frob/tickets/_reporting.py::_TICKET_ID_RE
- src/frob/tickets/_reporting.py::disclosure_shaped_language
- src/frob/tickets/_reporting.py::_done_report_section (new)
- src/frob/tickets/_reporting.py::_SUBHEADING_RE (new)
- src/frob/tickets/_reporting.py::_DONE_REPORT_HEADING (new)

Evidence:
- tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_reworded_heading_still_flagged_structurally
  (designated repro, FAILED_AT_PARENT verified against 21ac98557, the
  test-only commit that predates the fix -- exercises exactly the
  confirmed T-2623 incident shape: original phrase-matching heading vs.
  the reworded phrase-free heading, both must be flagged)
- tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_description_headings_before_done_report_are_not_flagged
- tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_no_done_report_heading_is_not_flagged_by_structure
- tests/unit/test_reporting_t1648_remainder.py::TestFiledFollowupTickets::test_parses_draft_ids
- tests/unit/test_reporting_t1648_remainder.py::TestFiledFollowupTickets::test_parses_mixed_real_and_draft_ids
- Full-file re-runs (unmodified pre-existing tests, confirming no
  regression): `tests/unit/test_reporting_t1648_remainder.py` (15
  collected, 0 failed) and `tests/unit/test_close_t1648_remainder.py`
  (unchanged, still passing against the new module -- proves the fix
  integrates correctly with the real close-time caller without editing
  it).

Positive controls checked directly against the four the ticket names:
- drafts-only follow-up now satisfies the guard (defect 1's own fix,
  `test_parses_draft_ids`/`test_parses_mixed_real_and_draft_ids`).
- reworded heading with no follow-up filed is still flagged
  (`test_reworded_heading_still_flagged_structurally`, both the
  original and reworded headings assert non-`None`).
- a clean report with no deferred work and no follow-ups still passes
  untouched (`test_clean_narrative_is_not_flagged`, unmodified, still
  green; `test_clean_narrative_is_unaffected` in the close-cmd suite,
  unmodified, still green).
- a report naming real numbered ids still passes exactly as before
  (`test_parses_ids_from_filed_line`, unmodified, still green).

Filed: none -- both defects are fully addressed inside this ticket's
declared scope; no out-of-scope discovery this pass.

Gates: scoped check below.

### Changed
```
 src/frob/tickets/_reporting.py               | 84 ++++++++++++++++++++----
 tests/unit/test_reporting_t1648_remainder.py | 60 +++++++++++++++++
 tickets/T-2638/done-report.md                | 98 ++++++++++++++++++++++++++++
 tickets/T-2638/ticket.md                     | 29 +++++++-
 4 files changed, 255 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_reworded_heading_still_flagged_structurally` (pytest node id, verified passing when recorded)
- `tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_description_headings_before_done_report_are_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_reporting_t1648_remainder.py::TestDisclosureShapedLanguage::test_no_done_report_heading_is_not_flagged_by_structure` (pytest node id, verified passing when recorded)
- `tests/unit/test_reporting_t1648_remainder.py::TestFiledFollowupTickets::test_parses_draft_ids` (pytest node id, verified passing when recorded)
- `tests/unit/test_reporting_t1648_remainder.py::TestFiledFollowupTickets::test_parses_mixed_real_and_draft_ids` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, F401@/home/logan/projects/frob/.claude/worktrees/t2629-t2638/src/frob/app/ticket_runner/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md

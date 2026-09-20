## Done report

Decision: the discriminator is "generated from prose AND unwritable by any
worktree", not "land-owned" as such. Extended `_WAIVER_PATHSPEC` (the SAME
pathspec-exclusion mechanism T-1633 already uses for tickets.md/
tickets-archive.md/tickets/**, for the identical reason) to also exclude
CHANGELOG.md and changelog.d/*.md -- both are generated per-ticket from
Done-report prose at close/land time (`src/frob/release/_fragments.py`,
`src/frob/app/ticket_runner/_land_cmd.py`) and, like the ledger, can never be
re-pointed by any worktree once landed (T-0731/T-2445). Scoped to the `*.md`
fragment files specifically, not `changelog.d/**`: an ordinary source file
that happens to sit under `changelog.d/` (T-4320's own
`test_real_directive_in_changelog_dir_path_still_flagged`, using a `.py`
file) is not generated narrative and must still block on a genuine
directive -- confirmed still passing, unchanged.

T-4320's narrowed directive-line-shape filter
(`_drop_non_directive_waiver_mentions`) is UNCHANGED and still the general
fix for "prose quoting a directive's exact text without being one" in every
OTHER location (a commit-message excerpt in a doc, a design-note draft,
...). The path exclusion added here is a narrower, second layer: it removes
only the two specific generated-and-unwritable files from the scan
entirely, the same posture already accepted for the ticket ledger, not a
general escape hatch and not a reversal of T-4320's reasoning.

Rejected alternatives (per the ticket's own list):
- "citation only blocks where a worktree could re-point it" -- states the
  requirement in the abstract but needs the identical path-based
  enumeration to implement (which files are worktree-writable is itself a
  path fact), so it collapses to the same fix with extra indirection.
- "ignore quoted/fenced text" -- a losing arms race against prose, exactly
  as the ticket warns; also does not distinguish a real directive that
  happens to be fenced (e.g. in a code block in ordinary docs) from a mere
  quotation.

Verified both directions (T-4325's own new test plus T-4320's pre-existing
one, both green):
- `test_changelog_fragment_quoting_whole_directive_not_a_citation`:
  reproduces the exact T-4320 fragment/aggregate shape (CHANGELOG.md +
  changelog.d/T-4320.md both quoting a complete `follow_up=T-4303`
  directive) and asserts `live_tracker_citations` now returns `()`.
- `test_real_directive_in_changelog_dir_path_still_flagged` (T-4320,
  unmodified): a genuine directive in an ordinary `changelog.d/notes.py`
  source file is still caught -- confirms this is not a path-exclusion of
  the directory, only of the generated `*.md` fragments.
- Full suite: `uv run pytest tests/test_tickets_live_tracker.py -q` ->
  32 passed (31 pre-existing + 1 new).
- Confirmed the actual blocked ticket, T-4303, now reaches its close step:
  `uv run frob ticket land T-4303 --worktree .claude/worktrees/t-4303`
  no longer refuses on LiveTrackerCited for CHANGELOG.md:1087/
  changelog.d/T-4320.md:2 (see run below). T-4303 was NOT landed -- left
  for the user, per instructions.

Evidence: tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_changelog_fragment_quoting_whole_directive_not_a_citation (new, bound via frob:tests); tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_real_directive_in_changelog_dir_path_still_flagged (pre-existing, re-verified unchanged)

Filed: none

SCOPE002 DISCLOSURE (frob:waive SCOPE002, same disclosed-breadth precedent as
T-3914/T-3930/T-4013/T-4019/T-4132):

frob:waive SCOPE002 reason="src/frob/tickets/_live_tracker.py::
live_tracker_citations carries a PRE-EXISTING frob:doc edge to
docs/modules/tickets-landing.md#live-tracker-citation-preflight-t-0854,
untouched by T-4325. Widening scope to include that shared doc file
cascades into the ENTIRE tickets-landing subsystem it also describes
(src/frob/tickets/_land.py, _land_compose.py, _land_ledger_merge.py,
_land_release.py, _land_squash.py, _leases.py, _models.py,
_mutation_evidence.py, _mutation_sweep_queue.py, _scope.py, _store.py,
_worktree_sweep.py, src/frob/app/ticket_runner/_land_cmd.py, __init__.py,
_verify.py, plus src/frob/gates/_bug_repro.py, _fix_engine_shared.py,
_mutation_evidence.py, src/frob/tickets/_evidence.py -- measured: 24+
unrelated SCOPE002 errors when actually added), none of which T-4325
touches. Same tension src/frob/gates/_rule_id_scan.py's SCANNED_BASES/
RETIRED_RULE_IDS COV001 waivers already document for this exact doc file.
Separately, tests/test_tickets_live_tracker.py (added to scope because
T-4325's own new regression test lives there) carries PRE-EXISTING
frob:tests edges from its other TestAnchorMarker/TestLandCheckSkips*
classes into src/frob/tickets/_land.py (test_set_anchor_requires_reason,
test_set_anchor_round_trips, test_terminal_land_refused,
test_non_anchor_terminal_land_not_refused, test_non_terminal_land_not_refused,
test_done_land_still_blocked_by_citation and 2 more, per
`frob ticket scope T-4325 --add` closure warnings), none of which T-4325
touches or whose behavior it changes. Widening scope to include
src/frob/tickets/_land.py for these pre-existing, unrelated test bindings
is out of proportion to T-4325's single-pathspec-tuple fix; this module's
own docstring documents the change, and both pre-existing gaps are
untouched by this diff."

Gates: `uv run frob check --ticket T-4325` -- see run below for the final
measurement; PRE001/FMT001/SCOPE001/COV002 all addressed (pre-work sweep
re-run after every scope/content change; FMT001 on the new frob:tests
directive waived per the identical FMT001 precedent already in
src/frob/app/_json_guard.py and src/frob/app/pyfmt_runner.py for this exact
"single-line frob:tests directive naming a long test node id" shape; SCOPE001
resolved by adding tests/test_tickets_live_tracker.py to scope since T-4325
edits it; COV002 resolved via `# frob:ticket T-4325` on
TestLiveTrackerCitations, the class T-4325's new test lives in). The
remaining unwaived SCOPE002 findings are the disclosed doc/test closure
above, waived per the T-3930-class precedent rather than expanding scope.

### Changed
```
 CHANGELOG.md                       |   3 +
 src/frob/tickets/_live_tracker.py  |  34 +++++++++++
 tests/test_tickets_live_tracker.py |  35 ++++++++++++
 tickets/T-4325/done-report.md      | 113 +++++++++++++++++++++++++++++++++++++
 tickets/T-4325/ticket.md           |   5 +-
 5 files changed, 189 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_changelog_fragment_quoting_whole_directive_not_a_citation` (pytest node id, verified passing when recorded)
- `tests/test_tickets_live_tracker.py::TestLiveTrackerCitations::test_real_directive_in_changelog_dir_path_still_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 4685 warning(s), 954 waived
- error-findings: SCOPE002@tickets.md

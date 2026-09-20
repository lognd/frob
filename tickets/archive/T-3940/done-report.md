## Done report

Fix: `_render001_checker` (the `_FILE_LOCAL_ERROR_CHECKERS` adapter for
RENDER001 at land time) filtered only on `.py`, so it scanned every
touched `.py` file in EVERY repo for a bare `print(...)`, refusing
consumer-repo lands (kicad-libsync's report) that have no `frob.render`
to route stdout through. It now calls `render001_scans(worktree,
rel_path)` -- the same public predicate `render_lint_gate` and
`_waive_audit` already use for RENDER001's scan set (`src/frob`,
`.claude/hooks`, `scripts/fleet_status.py`) -- so a bare print outside
that pathspec is silently out of scope, exactly like the gate itself.

Audit of the `_FILE_LOCAL_ERROR_CHECKERS` family (T-3940's own
requirement -- report every adapter, not only the reported one):

- `_render001_checker` (RENDER001): FROB-REPO-SPECIFIC rule
  (INV-RENDER-SOLE-STDOUT is about routing FROB's OWN stdout through
  `frob.render`). Was NOT scope-honoring -- fixed above.
- `_doc005_checker` (DOC005): NOT frob-repo-specific by construction --
  it only participates at all when the CONSUMING repo's own `frob.toml`
  declares a `[[docblocks.commands]]` entry (`_console_command_sources`
  reads that project-local, opt-in config and returns `()`, silently
  no-op, when absent). A repo with no such declaration -- every
  consumer repo that has not opted into DOC005 -- gets an empty
  `console_sources` and the checker returns `()` before ever inspecting
  `README.md`'s content. Its scope is therefore already correctly
  derived from the consuming repo's own state, not a second hardcoded
  frob-repo condition; no change needed.

The `_FILE_LOCAL_ERROR_CHECKERS` tuple holds exactly these two adapters
-- no other siblings to audit.

Fixtures (T-3940's three required, tests/test_ticket_work_and_land_finish.py):
- MUST-FIRE: TestAssertDiffDoesNotAddNewFileLocalErrors::
  test_a_new_render001_refuses_the_land -- a bare print under
  src/frob/ in the `repo` fixture still refuses.
- MUST-STAY-QUIET: TestAssertDiffDoesNotAddNewFileLocalErrors::
  test_a_bare_print_outside_the_render001_pathspec_does_not_refuse --
  a bare print under the fixture's generic src/ (no src/frob, no
  frob.render importable -- a real consumer-shaped tree, not a
  monkeypatched predicate) does not refuse.
- THIRD (desync-checkable): TestAssertDiffDoesNotAddNewFileLocalErrors::
  test_render001_checker_agrees_with_render001_scans_in_and_out_of_scope
  -- asserts _render001_checker's firing tracks render001_scans for
  both an in-scope and out-of-scope path with an identical bare print.

Also updated the two pre-existing RENDER001 land-time tests
(test_a_new_render001_refuses_the_land,
test_a_pre_existing_render001_merely_touched_does_not_refuse,
test_a_waived_new_finding_does_not_refuse) to use fixture paths under
src/frob/ -- before this fix they used a generic src/printer.py path
that was, by construction, OUTSIDE RENDER001's own pathspec and only
"fired" because the land-time checker ignored the pathspec entirely;
that was the bug encoded as a passing test.

Evidence:
tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrors::test_a_new_render001_refuses_the_land
tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrors::test_a_bare_print_outside_the_render001_pathspec_does_not_refuse
tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrors::test_render001_checker_agrees_with_render001_scans_in_and_out_of_scope
tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrors::test_a_pre_existing_render001_merely_touched_does_not_refuse
tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrors::test_a_waived_new_finding_does_not_refuse

Filed: none (the audit found no second defective adapter to file for)

Gates: `frob check --only scope --ticket T-3940` reports 28 pre-existing
SCOPE002 errors that are _land_cmd.py's own already-existing
frob:doc/frob:tests closure debt (unrelated to this diff -- confirmed
by reverting an attempted scope widen: closing them transitively
exploded to 247+ errors via unrelated doc/module edges, so the closure
is effectively unbounded for this hub file and out of this ticket's
scope to fix). `frob check --ticket T-3940`'s COV002 items on the new
test methods are resolved via frob:ticket T-3940 frob:tests directives
added to _render001_checker and frob ticket evidence above. `frob
check --only fmt --ticket T-3940`: 0 FMT/DSL errors after canonicalizing
the new directive line-wrapping (1 pre-existing, unrelated DRIFT001 on
src/frob/xref/__init__.py remains, not touched by this diff). gate:RENDER
itself: 0 errors, 4 waived (unaffected by this fix). frob test --base
main: exit=0, 5 test(s) recorded stable.

### Changed
```
 tickets/T-3940/ticket.md | 368 +++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 368 insertions(+)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrors::test_a_new_render001_refuses_the_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrors::test_a_bare_print_outside_the_render001_pathspec_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrors::test_render001_checker_agrees_with_render001_scans_in_and_out_of_scope` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrors::test_a_pre_existing_render001_merely_touched_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrors::test_a_waived_new_finding_does_not_refuse` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 4 error(s), 4389 warning(s), 929 waived
- error-findings: DOC006@tickets/T-3931/ticket.md, DRIFT001@src/frob/xref/__init__.py, PRE001@tickets/T-3940, SCOPE002@tickets.md

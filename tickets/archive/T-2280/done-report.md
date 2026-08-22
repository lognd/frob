## Done report

### What changed

Generalizes T-2214's ARCH001-only "does not worsen" land-time gate to
every ERROR-severity rule that has (or gets) a registered file-local
checker. `src/frob/app/ticket_runner/_land_cmd.py`:

- `_render001_checker(rel_path, text) -> tuple[Violation, ...]`: adapter
  reusing `frob.gates._render_lint`'s own `_scan_python_prints`/
  `_render001_violation` (not a reimplementation).
- `_FILE_LOCAL_ERROR_CHECKERS`: the registry, documented as the extension
  point for future file-local ERROR rules.
- `_file_local_error_violations_for_content`: runs every registered
  checker against one file's text, keeping only `Severity.ERROR` findings
  -- this is where criterion 3 (severity-derived, not a rule-name
  allowlist) is enforced: a checker's own NEW error-severity sub-finding
  is picked up automatically, no edit needed here.
- `_violation_identity`: a line-shift-tolerant identity (`v.symref` when
  set, else the message with its `:LINE` token stripped), so an edit
  elsewhere in the same file that merely shifts a pre-existing finding's
  line number does not register as "new".
- `_new_file_local_errors_in_file`/`_new_file_local_errors_in_diff`:
  T-2214's own two-content (current worktree vs `git show` merge-base
  scratch copy) shape, generalized, multiset (`Counter`)-compared rather
  than set-compared so N-vs-N+1 identical-identity sites are still caught.
- `_unwaived_file_local_error_findings`/`_log_file_local_error_refusals`:
  split out of the main assertion (kept it under ARCH001's own 60-line
  threshold and away from ARCH103's mixed-concerns trip) -- waiver check
  reuses T-2214's own `_frob_directive_block`/`_genuine_comment_lines`
  mechanism unchanged, no second waiver system invented.
- `_assert_diff_does_not_add_new_file_local_errors_pre_land`: wired into
  `_land_core_prepare` immediately after T-2214's own call, same
  unconditional-across-every-profile posture.

### Why only RENDER001 is registered (not SELFAUDIT001/DOC005/ARCH103)

T-2280's own required shape -- current-file-content vs merge-base-file-
content, "two small parses per touched file", reusing T-2214's
comparison rather than inventing a second one -- only fits a rule whose
finding is computable from ONE file's own text, no repo-wide graph.
Checked all three named in the ticket's own measured evidence:

- **RENDER001**: file-local (`ast.parse` + a pure AST walk). Registered.
- **DOC005**: targets `README.md`/the CLI command table specifically, not
  arbitrary touched files -- it would essentially never fire under a
  per-touched-file diff unless README.md itself is the touched file, and
  even then its check compares the table against the CLI parser tree
  (cross-module), not the file's own prior content. Does not fit this
  shape.
- **SELFAUDIT001**: evaluates frob's OWN design/compliance state
  (`evaluate_compliance`, mode/reliability conformance) -- not
  attributable to any particular touched FILE at all. Does not fit this
  shape by construction.
- **ARCH103**: SRP/cohesion classification needs the call graph
  (`analyze_project`), the exact repo-wide cost this gate exists to
  avoid paying at land time. Does not fit this shape.

These three genuinely need cross-file/repo-wide context frob does not
have a bounded, land-time-affordable way to compute today. Filed as a
scoped follow-up rather than widened into this ticket (see Filed, below).
This is a real, honest gap: T-2280's own measured evidence names 4
regressed rules and this land covers 1 of them at land time (RENDER001);
the registry is built so DOC005/SELFAUDIT001/ARCH103 support, when it
lands, is a same-shaped follow-up ticket adding an entry, not a redesign.

### Evidence (acceptance criteria)

1. `test_a_new_render001_refuses_the_land` (T-1929 designated repro,
   FAILED_AT_PARENT confirmed against 51489e1b6, the test-only commit):
   a bare `print()` in a new file with no merge-base equivalent refuses
   the land, naming rule/file/line.
2. MUST-STILL-PASS controls, all bound: `test_a_clean_land_is_unaffected`
   (no findings -> unaffected), `test_a_pre_existing_render001_merely_
   touched_does_not_refuse` (pre-existing print, trailing-comment-only
   diff -> not refused), `TestAssertDiffDoesNotWorsenLongFunctions::
   test_a_new_over_threshold_function_refuses_the_land` (T-2214's own
   ARCH001 test, unchanged, still green -- ARCH001 behavior verified
   untouched), `test_unmeasurable_diff_reports_skipped_unmeasured_and_
   lands` (working_diff failure -> WARNING containing "SKIPPED-
   UNMEASURED", returns without raising).
3. Severity-derivation: enforced in `_file_local_error_violations_for_
   content`'s `if v.severity == Severity.ERROR` filter, exercised by
   `test_a_new_render001_refuses_the_land` (RENDER001 IS Severity.ERROR;
   a checker emitting only WARN/UNRESOLVED would never reach the
   comparison at all -- no rule-name check anywhere in the participation
   path).
4. Refusal message: `_log_file_local_error_refusals` names rule, file,
   line, the underlying violation message (which itself names the fix),
   and the exact `frob:waive <RULE> reason="..."` escape hatch, in one
   `_log.error` call -- same message shape T-2214's own ARCH001 refusal
   uses. Also verified: `test_a_waived_new_finding_does_not_refuse`
   confirms the waiver half of that same message actually works (a real
   `frob:waive RENDER001` comment suppresses the refusal).
5. Wall-clock: measured directly, `.venv/bin/python3` timing
   `_assert_diff_does_not_add_new_file_local_errors_pre_land` against
   THIS ticket's own 2-file diff (its largest realistic input so far):
   **0.067s** (67ms), both before and after the ARCH001/PERF004/WIRE001
   cleanup pass. T-2214's own ARCH001 check pays the identical per-file
   cost already; this adds one more per-file checker call on the same
   two parses, not a second full traversal. Nowhere close to "minutes" --
   T-1684's own removed cost (a full unscoped `frob check`, measured at
   87.6s wall-clock even with a warm gate cache in this same worktree)
   is NOT reintroduced.

### Self-check (dogfooding)

Ran the new gate against its OWN diff before committing the fix
(`_assert_diff_does_not_add_new_file_local_errors_pre_land(worktree,
"T-2280", {"_land_cmd.py", "test_ticket_work_and_land_finish.py"})`):
clean, no new RENDER001 (or any other registered rule) introduced by
this ticket's own diff.

### Gates

`frob check --ticket T-2280`: iterated to a clean state for the touched
files specifically -- fixed E501 (4 lines), a `dict[str, list[int]]` ->
`dict[str, frozenset[int]]` type annotation (`ty` caught this), PERF004
(hoisted `sorted()` out of the per-identity loop into one sort +
`itertools.groupby`), WIRE001 (added a `frob:waive` for the
registry-tuple indirect-dispatch shape, following `frob.gates._arch`'s
own precedent for the identical pattern) plus its own WIRE002 follow-up
requirement. Remaining findings in `_land_cmd.py`/`test_ticket_work_
and_land_finish.py` after this pass are ALL pre-existing (verified by
line number: 1950/2976/3424/3496/3580/1753/3475/740, none inside this
ticket's own new code, which spans roughly line 3727-4050).

### Filed

T-2285 (renumbers at land): "Extend T-2280's file-local
pre-land error gate to DOC005/SELFAUDIT001/ARCH103" -- the follow-up for
"Why only RENDER001" above, medium priority, feature-kind.

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py   | 299 ++++++++++++++++++++++++++++++
 tests/test_ticket_work_and_land_finish.py | 143 ++++++++++++++
 tickets/T-2280/ticket.md                  |  36 +++-
 tickets/T-2285/ticket.md        |  24 +++
 4 files changed, 495 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrors::test_a_new_render001_refuses_the_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrors::test_a_clean_land_is_unaffected` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrors::test_a_pre_existing_render001_merely_touched_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_new_over_threshold_function_refuses_the_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrors::test_unmeasurable_diff_reports_skipped_unmeasured_and_lands` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2280/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2280/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2280/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2280, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md

## Done report

### Per-rule coverage decisions

**DOC005 -- GATED (partial: STALE rows + count-claim mismatches only).**
Registered `_doc005_checker` in `_FILE_LOCAL_ERROR_CHECKERS`. DOC005's own
implementation (`frob.gates._docblocks`) needs one external truth beyond
README.md's own text -- the live subcommand tree, built via
`_console_command_sources`/`_console_trees` (a single `argparse` walk).
Measured (T-2285, this worktree): **~51ms** to build, well inside T-2280's
"two small parses per file" cost class, NOT a repo-wide
`analyze_project`/`GraphSnapshot` build. Widened the checker interface
from `(rel_path, text)` to `(worktree, rel_path, text)` so a checker can
receive this external truth; `_render001_checker` ignores the new
parameter (interface parity, not a behavior change).

Only STALE (a README row naming a subcommand that no longer exists) and
the count-claim mismatch are gated -- both are genuinely attributable to
README.md's OWN diff (its content changed against a truth held constant
across both the old-content and new-content calls). MISSING (a live
subcommand with no row at all) is deliberately excluded: it fires when
the LIVE TREE changes, not when README.md's own content changes -- not
attributable to this file's diff, the same "attributable, not global"
line T-2214/T-2198 already drew for ARCH001/TICK. The cli.md
generator-freshness half (`_doc005_cli_table_freshness_violations`) is
also excluded: it's a `frob docs sync-commands` freshness check against
generated output, a different mechanism, out of this ticket's registry
shape.

**SELFAUDIT001 -- NOT GATED, does not fit the model at all.**
`_selfaudit_violations` folds `check_self_conformance`/`check_mode_
conformance`/`check_reliability_timeouts`/`check_reliability_health` --
frob's own design/compliance/reliability STATE, evaluated against
`design/` files and runtime health, not any particular touched file's
content. There is no "old file content vs new file content" comparison
that means anything here: a SELFAUDIT001 finding is not attributable to
a specific file's diff the way ARCH001/RENDER001/DOC005 are. Gating this
at land time would need an entirely different mechanism (comparing the
FULL evaluation's outcome before/after, not a per-file diff) -- out of
this ticket's registry-shaped scope. Not forced.

**ARCH103 -- NOT GATED, cost-prohibitive.**
`arch_gate`'s ARCH103 findings come from `analyze_project(root, ...)`,
the repo-wide call-graph build T-2280's own registry was designed to
avoid. Measured directly in this worktree:

    analyze_project elapsed: 19.83s (471 suggestions, this repo's real size)

Running this ONCE per land already costs more than 100x DOC005's
external-truth build; running it TWICE (current + merge-base, T-2214's
own shape) would cost ~40s on every single land. The land path is
already the fleet's bottleneck (T-1684 exists specifically to keep a
full `frob check` off it) -- adding tens of seconds per land to gate one
rule class is not an acceptable trade, so ARCH103 is deliberately left
ungated. A future fix would need either a genuinely incremental/
per-symbol SRP evaluator (does not exist today) or accepting a
materially different, coarser-grained land-time cost model than this
registry's -- real, tracked work, not implemented here.

### Wall-clock (criterion 5, per-rule)

Measured with `.venv/bin/python3` timing
`_assert_diff_does_not_add_new_file_local_errors_pre_land` directly:

- RENDER001 alone, 2 touched files (T-2280's own baseline): **0.067s**.
- RENDER001 + DOC005, 3 touched files (this ticket's own diff, README.md
  included): **0.234s** -- the ~167ms delta is DOC005's own external-truth
  build running twice (once per side of the comparison, ~51ms each) plus
  one extra `git show`/file-read round trip.
- ARCH103 (NOT added -- reference point only): a single `analyze_
  project` call alone is 19.83s; would need to run twice per land under
  T-2214's shape, ~40s -- this is exactly the number that kept ARCH103
  out.

Nowhere near "minutes" for what shipped; ARCH103's cost is exactly why it
did not ship.

### MUST-STILL-PASS

- `TestAssertDiffDoesNotAddNewFileLocalErrors` (T-2280's own RENDER001
  suite, unchanged): all 5 tests still pass, behavior identical.
- `TestAssertDiffDoesNotWorsenLongFunctions` (T-2214's own ARCH001 suite,
  untouched): all 6 tests still pass.
- `TestAssertDiffDoesNotAddNewFileLocalErrorsDoc005` (new, T-2285): 3
  tests -- new STALE row refuses, pre-existing STALE row merely touched
  does not refuse, no `[[docblocks.commands]]` config is a no-op (fail-
  open, matching `doc005_gate`'s own posture for an unconfigured repo).
- SKIPPED-UNMEASURED path: unchanged, exercised by T-2280's own
  `test_unmeasurable_diff_reports_skipped_unmeasured_and_lands`
  (the comparison entry point is shared, not duplicated per rule).

### Evidence

- `TestAssertDiffDoesNotAddNewFileLocalErrorsDoc005::test_a_new_stale_row_refuses_the_land`
  (T-1929 designated repro, FAILED_AT_PARENT confirmed against 762305a9c,
  the test-only commit).
- `::test_a_pre_existing_stale_row_merely_touched_does_not_refuse`.
- `::test_no_docblocks_config_is_a_no_op`.
- `TestAssertDiffDoesNotAddNewFileLocalErrors::test_a_new_render001_refuses_the_land`
  (T-2280's own RENDER001 test, still green -- must-still-pass).
- `TestAssertDiffDoesNotWorsenLongFunctions::test_a_new_over_threshold_function_refuses_the_land`
  (T-2214's own ARCH001 test, still green -- must-still-pass).

### Land friction avoided

T-2280's own WIRE001 waiver `follow_up="T-2280"` blocked ITS OWN close
last time (LiveTrackerCited). Checked this ticket's own new waivers
before landing: both the re-pointed T-2280 waiver and the new
`_doc005_checker` waiver cite `follow_up="T-2057"` -- an open, unrelated
ticket, never T-2285 itself.

### Gates

`frob check --ticket T-2285`: 2 new E501 findings (long `frob:waive`
directive lines) fixed by rewording; all remaining findings in
`_land_cmd.py`/`test_ticket_work_and_land_finish.py` are pre-existing
(verified by line number against T-2280's own Done report's catalogue).

### Filed

None.

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py   | 169 +++++++++++++++++++++++-------
 tests/test_ticket_work_and_land_finish.py |  90 ++++++++++++++++
 tickets/T-2285/ticket.md                  |  17 ++-
 3 files changed, 238 insertions(+), 38 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrorsDoc005::test_a_new_stale_row_refuses_the_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrorsDoc005::test_a_pre_existing_stale_row_merely_touched_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrorsDoc005::test_no_docblocks_config_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotAddNewFileLocalErrors::test_a_new_render001_refuses_the_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_new_over_threshold_function_refuses_the_land` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2285/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2285/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2285/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2285/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2285/tests/test_ticket_land.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2285, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md

## Done report

Decision: --output is the PARENT directory (semantics (a)), matching
docs/commands/scaffold.md's existing quickstart text and the reporter's own
expectation from ../diax FROBLEMS F-001. render_project now resolves every
manifest entry under output_dir/name instead of output_dir directly -- a
one-line change at the join point, so it applies uniformly to all six
scaffold manifests, verified via
tests/unit/test_scaffold_project.py::test_render_project_all_registered_types_succeed
and test_render_project_all_types_default_to_rapid_profile (both iterate
list_project_types()).

This also structurally resolves the "ALSO IN SCOPE" scatter concern without
a separate project-root guard: every render lands under output_dir/name, so
the bare no-output form can no longer place files loose into the caller's
cwd regardless of what that directory already contains -- proven by
test_render_project_bare_form_does_not_scatter_into_existing_project_root.

Fixtures:
- MUST-FIRE: test_render_project_creates_name_subdir_must_fire
- MUST-STAY-QUIET: test_render_project_existing_collision_still_refuses_must_stay_quiet
- THIRD: test_render_project_bare_form_does_not_scatter_into_existing_project_root

Known pre-existing, out-of-scope failure (verified identical on unmodified
main before this ticket's commit, not caused by this change):
tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately
still fails at the `frob check` step on a freshly scaffolded project
(SCHEMA001 UNMEASURED gates from a stale global frob install, REF/OPAQUE
findings in the template's own generated content). This is T-3277's stated
scope: "determine whether the test already encodes this and is simply not
green" -- confirmed yes; T-3277 is "make it pass and widen it", not
"write it". frob test --base main confirms this is the only failure in the
touched-set run.

Filed: none.

Gates: frob check --ticket T-3271 --only scope --only prework clean (the
SCOPE001 scope-closure warnings surfaced after `scope --add` were pre-
existing broad closure suggestions unrelated to this diff, not new
violations). frob ticket sweep T-3271 re-run after scope --add. frob test
--base main: touched-set green except the documented pre-existing failure.

### Changed
```
 docs/commands/scaffold.md           |  2 +-
 src/frob/_cli_parsers/_core.py      |  8 ++++-
 src/frob/scaffold/project.py        |  8 ++++-
 tests/system/test_scaffold_dx.py    |  4 ++-
 tests/unit/test_scaffold_project.py | 69 ++++++++++++++++++++++++++++++++++---
 tickets/T-3271/ticket.md            | 24 ++++++++++++-
 6 files changed, 106 insertions(+), 9 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

## Done report

Root cause established via a direct positive control before any change:
`.claude/hooks/dispatch-telemetry.py` (confirmed to contain a `subprocess`/
`_run_git` call) was NEVER visited by `walk_pruned` -- `walk_pruned(root)`
returned 0 files under `.claude/hooks` even though all 13 files there are
git-tracked and not gitignored. This is the "scanner never visited" shape,
not "visited and found empty": T-4178's `_load_repo_ignore_globs` merges
this repo's own `.gitignore` lines (including `!`-negations) into
`walk_pruned`'s exclude set, but `_should_prune_dir`'s pre-existing
`f"{rel}/."` synthetic-child probe (added to make `prefix/**`-style globs
match a bare directory) has no way to see a negation targeting a child
below the probed directory. This repo's own `.gitignore` uses exactly that
shape -- `.claude/*` plus `!.claude/hooks/**` -- so `.claude` itself was
pruned wholesale before `os.walk` ever descended into it, taking
`.claude/hooks/**` down with it.

Fix: `_has_negated_descendant` (src/frob/excludes.py) checks whether any
`!`-negation glob targets something under the directory `_should_prune_dir`
is about to prune; if so, the directory is NOT pruned early and per-file
`is_excluded` (which correctly runs the negation-aware `PathSpec.match_file`)
decides file-by-file on the way through, exactly as real gitignore semantics
require. Verified directly: `walk_pruned` now yields all 13
`.claude/hooks/**` files, while `.claude/worktrees/**`, `.claude/scratch/**`,
`.claude/hooks/state/**`, and `.claude/settings.local.json` remain correctly
pruned/excluded (no regression).

Changed:
src/frob/excludes.py::_has_negated_descendant
src/frob/excludes.py::_should_prune_dir
tests/test_excludes.py::TestWalkPrunedHonorsIgnoreFile::test_negated_reinclusion_not_pruned_wholesale

Evidence:
tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_baseline_sys101_is_zero (was failing, now passes: baseline_sys101_count == 0)
tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_no_undetectable_kinds
tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing
tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant (was failing on the four claude_hooks SYS101 violations, now passes with violations == ())
tests/test_excludes.py::TestWalkPrunedHonorsIgnoreFile::test_negated_reinclusion_not_pruned_wholesale (new regression test, reproduces the .claude/* + !.claude/hooks/** shape directly)
Also re-ran clean: tests/unit/strata/test_selfconform.py::TestCoverageTotality, tests/test_excludes.py (full file, 29/29), tests/unit/strata/test_mutation_audit.py (4/4), tests/system/test_frob_self_model.py, tests/unit/test_lang_strata.py, tests/test_graph.py (196/196)

Filed: none

Gates: `frob check --ticket T-4306` -- gate:SYS/gate:COV/gate:PRE/gate:LANDFMT/ruff-check/ruff-format/ty all clean for this change. Four unrelated gate families still report pre-existing, out-of-scope findings, confirmed by direct inspection to be unrelated to this diff:
- gate:ARCH (3 errors, all in src/frob/graph/cache.py, ARCH103 complexity, untouched by this ticket)
- gate:SCOPE (73 errors, all `design/frob.strata::*` symbols whose `frob:doc`/`frob:tests` targets sit outside T-4306's scope -- this is design/frob.strata's own pre-existing doc-closure surface, present the moment the ticket was auto-planned with scope=['design/frob.strata'], before any code was touched; the three closure entries actually caused by widening scope to src/frob/excludes.py (docs/modules/app.md, tests/test_excludes.py, tests/unit/gates/test_ffi_boundary_path_shape.py) were added to scope and are resolved)
- gate:TODO (1 error, src/frob/gates/_land_format.py, unrelated frob:todo binding)
- gate:WIRE (1 error, tests/test_ci_workflow_timeout.py, unrelated stale waiver)
Per the ticket's own instruction ("Other failures in the same suite are not yours"), these are left unwaived and unfixed as out of scope.

### Changed
```
 tickets/T-4306/ticket.md | 79 ++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 79 insertions(+)
```

### Evidence
- `tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_baseline_sys101_is_zero` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_no_undetectable_kinds` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)
- `tests/test_excludes.py::TestWalkPrunedHonorsIgnoreFile::test_negated_reinclusion_not_pruned_wholesale` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 4 error(s), 4660 warning(s), 952 waived
- error-findings: ARCH103@src/frob/graph/cache.py, SCOPE002@tickets.md, TODO002@src/frob/gates/_land_format.py, WIRE002@tests/test_ci_workflow_timeout.py

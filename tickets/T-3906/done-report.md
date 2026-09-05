## Done report

DECISION: consolidate under `frob format`, not a bare rename. Both names
were already the same word for two different operations; a rename would
only relabel the confusion. Followed the explore/quality/design/ops
precedent (T-1238/T-1567/T-1568/T-1569): "--code"/"--directives" scope
which half runs (neither flag runs both, the pre-consolidation default),
"--check"/"--json" apply uniformly to whichever half(ves) ran. "frob fmt"
survives as a real, working frob:deprecated alias (sunset 2026-12-01,
ticket T-3911) for "frob format --directives" so every existing
invocation keeps working through the sunset window -- following the same
groups' standalone-usability property.

CALLER ENUMERATION (measured via git grep, CHANGELOG.md/tickets excluded):
- Makefile format:/lint-fix: targets -- updated to pass --code explicitly
  (bare "frob format" now also runs the directive half by default; --code
  keeps these two targets' pre-consolidation ruff-only scope unchanged).
- src/frob/scaffold/data/shared/python/{Makefile.j2,README.md.j2,docs/index.md.j2}
  -- comment text updated to describe the new default (ruff + directive
  canon) for newly-scaffolded projects.
- docs/commands/format.md -- rewritten for the consolidated surface.
- docs/modules/cli.md's generated command table -- regenerated via
  frob.gates._docblocks.sync_cli_command_table (byte-identical to what
  frob check's own DOC005 gate expects).
- docs/modules/app.md, docs/modules/gates.md -- runner/gate docs updated
  with the consolidated surface and the deprecation note.
- Every remedy string naming "frob fmt <path>" (FMT001's hint in
  src/frob/gates/_todo_fmt.py, the rule-catalog comment in
  src/frob/gates/_waive.py, the pre-land absorption step in
  src/frob/app/ticket_runner/_land_cmd.py, doc mentions in
  docs/guides/agent-playbook*.md, docs/modules/tickets-landing.md) --
  left unchanged and verified still resolving, because "frob fmt" is a
  real working alias, not a broken/renamed verb; the T-3859 failure mode
  (a remedy naming a flag the verb no longer accepts) does not apply.
- docs/modules/gates.md's own edit was reverted: adding it to this
  ticket's scope triggered T-3902's known SCOPE002 closure explosion
  (the file is a scope-closure hub with hundreds of doc edges); the one
  paragraph I wanted to add there is not essential and is deferred to a
  follow-up once T-3902 is fixed.
- README.md: NOT touched (Series FG owns T-3907's README rewrite). The
  row that needs updating once FG or a follow-up picks it up:
  "frob fmt" / "frob format" (currently two separate rows describing the
  pre-consolidation split) should become one row for "frob format"
  ("--code"/"--directives"/"--check"/"--json") plus a note that
  "frob fmt" is a deprecated alias, sunset 2026-12-01.

--CHECK GAP CLOSED for code formatting regardless of the consolidation
decision: pyfmt_runner.py now has --check for both the full-rule-set path
(delegating to frob.check._python._run_ruff, the existing check-only
lint+format primitive) and the --select-imports-only path (two new local
helpers, _run_ruff_check_select_imports_no_fix/_ruff_format_check_only,
mirroring the existing write-mode pair).

T-3312 folded in: format_paths/fmt_paths are both lists now (nargs="*",
default ["."]), for both the consolidated verb and the deprecated alias.

Deprecation: frob:deprecated 0.1.0 sunset="2026-12-01" ticket="T-3911" on
fmt_runner.py::run. T-3911 filed and tracks the actual removal at sunset.

BLOCKER-adjacent finding, NOT fixed here (out of scope, filed instead):
T-3912 -- DEPR003 (a frob:deprecated still inside its warning window) is
documented as Severity.WARN in src/frob/gates/_debt_deprecated.py's own
docstring, but frob check --json's raw diagnostic for this ticket's own
new (first-ever live) frob:deprecated directive reports severity "error"
-- a genuine mismatch between the gate's documented behavior and its
observed output, not something this ticket's scope (app.py/pyfmt_runner/
fmt_runner/_cli_parsers/_misc.py/config.py) can safely fix. Left
un-waived (a waiver would misrepresent a genuine, temporary in-window
deprecation as permanently fine) -- T-3912 tracks the actual fix.

Also filed while enumerating callers: this ticket's own body needed two
backtick fixes (DOC006 read the proposed --directives/--check flags as
resolvable CLI pointers before they existed) -- fixed in this worktree's
copy of tickets/T-3906/ticket.md per the coordinator's direction.

Changed:
- src/frob/app/pyfmt_runner.py (consolidated run(), --code/--directives/
  --check/--json, _resolve_scope/_run_code_half/_render_human, two new
  check-only ruff helpers)
- src/frob/app/fmt_runner.py (deprecated alias: unchanged formatting
  behavior, T-3312 paths list, frob:deprecated directive, deprecation
  notice on stderr so --json stays parseable, _render_fmt_report split
  out for ARCH001)
- src/frob/_cli_parsers/_misc.py (_add_format_parser rewritten,
  _add_fmt_parser documents the deprecation, both take nargs="*" paths)
- src/frob/app/config.py (format_code/format_directives/format_check/
  format_json/format_include_test_corpora added; fmt_path/format_path ->
  fmt_paths/format_paths)
- src/frob/app/_config_external.py (field-tuple wiring for the above --
  this is what silently broke my first pass: the new CLI flags/paths
  parsed correctly but never reached AppConfig until this file's
  _PATH_FIELDS/_LIST_FIELDS/_BOOL_FLAGS tuples were updated)
- Makefile, scaffold templates, docs/commands/format.md,
  docs/modules/{app,cli}.md, tests/unit/test_pyfmt_runner.py (consolidated
  + T-3312 + deprecated-alias tests, all mock-based matching this file's
  own established no-real-filesystem pattern), tests/unit/test_makefile_coverage.py,
  tests/unit/test_app_runners_json_guard_t2492.py,
  tests/unit/test_app_runners_t0875_leaf_collision.py,
  tests/unit/test_fmt_wiring_reachability_t2761.py (fmt_path->fmt_paths
  field rename)

Filed: T-3911 (fmt alias sunset-removal follow-up), T-3912 (DEPR003
severity-vs-docstring mismatch, out of this ticket's scope)

Evidence: 14 pytest node ids bound via `frob ticket evidence`, covering
the consolidated verb's --code/--directives/--check scoping, the T-3312
multi-path fold-in, the two new check-only ruff helpers, and the
deprecated alias's continued behavior + deprecation notice.

Gates: `frob check` (no --ticket, full repo): 6 errors, all pre-existing/
unrelated to this ticket's diff except DEPR003 (T-3912, filed, out of
scope) -- the other 5 are T-3886/T-3902's own pre-existing DOC006 hits,
docs/guides/quickstart.md's pre-existing REF002, and PRE001/SCOPE001's
"pass --ticket" advisory on the bare diff. `frob check --ticket T-3906`
additionally surfaces T-3902's own known SCOPE002 closure-explosion
class (app.py/config.py/_cli_parsers/_misc.py fan out into hundreds of
doc/test edges under strict per-ticket closure) -- not something this
ticket can resolve without an unbounded scope expansion into unrelated
files; T-3902 already tracks the underlying defect.
`frob test --base main`: touched-set green (25 outcomes recorded).

### Changed
```
 Makefile                                           |   9 +-
 docs/commands/format.md                            |  72 ++++--
 docs/modules/app.md                                |  25 +-
 docs/modules/cli.md                                |   4 +-
 docs/modules/gates.md                              |  11 +-
 src/frob/_cli_parsers/_misc.py                     |  76 ++++--
 src/frob/app/_config_external.py                   |  13 +-
 src/frob/app/config.py                             |  45 +++-
 src/frob/app/fmt_runner.py                         | 107 ++++++---
 src/frob/app/pyfmt_runner.py                       | 254 +++++++++++++++++----
 src/frob/scaffold/data/shared/python/Makefile.j2   |   2 +-
 src/frob/scaffold/data/shared/python/README.md.j2  |   2 +-
 .../scaffold/data/shared/python/docs/index.md.j2   |   2 +-
 tests/unit/test_app_runners_json_guard_t2492.py    |   2 +-
 .../unit/test_app_runners_t0875_leaf_collision.py  |   2 +-
 tests/unit/test_fmt_wiring_reachability_t2761.py   |   4 +-
 tests/unit/test_makefile_coverage.py               |  11 +-
 tests/unit/test_pyfmt_runner.py                    | 248 +++++++++++++++++++-
 tickets/T-3906/ticket.md                           |  96 +++++++-
 tickets/T-3911/ticket.md                           |  32 +++
 tickets/T-draft-ea567293/ticket.md                 |  30 +++
 21 files changed, 885 insertions(+), 162 deletions(-)
```

### Evidence
- `tests/unit/test_pyfmt_runner.py::TestRun::test_default_delegates_to_run_ruff_autofix` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestRun::test_select_imports_only_uses_dash_dash_select_i` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestRun::test_nonzero_exit_propagates` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestRunCheckModeDoesNotWrite::test_check_mode_does_not_write` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestRunCheckModeDoesNotWrite::test_check_mode_nonzero_exit_on_dirty_tree` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestRunScopeFlags::test_code_only_skips_directives` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestRunScopeFlags::test_directives_only_skips_ruff` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestRunMultiplePaths::test_multiple_paths_each_get_processed` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestFormattedTreePassesCheckCleanly::test_clean_tree_check_exits_zero_for_both_halves` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestDeprecatedAliasStillWorks::test_fmt_alias_still_formats_and_warns` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestRunRuffCheckSelectImportsNoFix::test_missing_binary_yields_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestRuffFormatCheckOnly::test_missing_binary_yields_typed_result` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestFormatLintTypecheckRecipesDelegateToFrob::test_format_calls_frob_format_select_imports_only` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestFormatLintTypecheckRecipesDelegateToFrob::test_lint_fix_calls_frob_format_full_rule_set` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 14 passed (from 14 evidence id(s))
- gates: 6 error(s), 4360 warning(s), 931 waived
- error-findings: DEPR003@src/frob/app/fmt_runner.py, DOC006@tickets/T-3886/ticket.md, DOC006@tickets/T-3902/ticket.md, PRE001@tickets/T-3906, REF002@docs/guides/quickstart.md, SCOPE002@tickets.md

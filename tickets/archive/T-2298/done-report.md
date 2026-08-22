## Done report

Changed:
  src/frob/gates/_fmt_directives.py::_is_test_corpus_path (new)
  src/frob/gates/_fmt_directives.py::_TEST_CORPUS_SUFFIXES (new)
  src/frob/gates/_fmt_directives.py::_format_one_path (new include_test_corpora param)
  src/frob/gates/_fmt_directives.py::format_paths (new include_test_corpora param, default False)
  src/frob/app/fmt_runner.py::run (wires cfg.fmt_include_test_corpora through)
  src/frob/app/config.py::AppConfig (new fmt_include_test_corpora field)
  src/frob/app/_config_external.py (new field added to the bool-fields list)
  src/frob/_cli_parsers/_misc.py::_add_fmt_parser (new --include-test-corpora flag)

Chose direction (b) from the ticket's own list: `.strata` fixture
directories are excluded from `frob fmt` by default, opt-in via an
explicit flag. Direction (a) (scope fmt to the invoking ticket's declared
scope) was not reachable cheaply from `format_paths`'s own call sites --
`_land_cmd.py`'s `_fmt_pre_land_step` ALREADY does exactly that scoping
(T-1404, scoped to the ticket's touched-file set when computable, falling
back to a whole-tree call only when it cannot be computed) and calls
`format_paths` per-file for the scoped case, so the ticket-scope link
already exists one layer up; `format_paths` itself has no ticket context
to reach for. Direction (b) closes the concrete incident directly at the
one shared function every caller goes through.

`format_paths(root, ..., include_test_corpora=False)` (the new default)
now skips a `tests/**/*.strata` file when it is reached via a BROAD
path's expanded walk (`iter_files`) -- `_is_test_corpus_path` matches a
`.strata` suffix combined with a `tests` path component. A file named
EXPLICITLY as `root` (a single file, not a directory walk) is still
formatted regardless -- that is a deliberate, scoped request, not the
broad-walk incident this closes, and matches `_land_cmd.py`'s own
per-file touched-set call shape (T-1404), which must keep working
unchanged when a ticket's real scope legitimately includes a fixture
file it is intentionally editing.

Every existing `format_paths` call site was checked (`git grep
format_paths`): `_land_cmd.py`'s two calls (whole-tree fallback + scoped
per-file), `_fix_engine_text.py`'s two calls, and the CLI runner --
none pass `include_test_corpora=True`, so all now inherit the safe
default automatically. `_land_cmd.py`'s whole-tree fallback path (used
when a ticket's touched-set cannot be computed) is the closest analogue
to the reported incident (`frob fmt .` with a broad path) and is now
protected the same way at land time, not just from the CLI.

Evidence:
  tests/test_gates_fmt_directives.py::TestFormatPaths::test_broad_path_formats_source_but_leaves_strata_fixtures_untouched
    (accepts [0],[1], designated repro -- FAILED_AT_PARENT confirmed at
    dbdecec7b, a test-only commit with the fix not yet applied; also the
    POSITIVE CONTROL the ticket's own acceptance demands -- asserts
    source.py DOES get formatted, not merely that the fixture is
    untouched, so a fix that broke fmt entirely would also fail this)
  tests/test_gates_fmt_directives.py::TestFormatPaths::test_include_test_corpora_opts_back_in
    (accepts [0] -- the exclusion is a default, not a hard block)
  tests/test_gates_fmt_directives.py::TestFormatPaths::test_explicit_single_fixture_path_is_still_formatted
    (accepts [0] -- explicit single-file targets, matching _land_cmd.py's
    own T-1404 touched-set call shape, are unaffected)
  tests/test_gates_fmt_directives.py::TestFormatPaths::test_write_mode_rewrites_file
    (accepts [0] -- pre-existing positive control, still passes: ordinary
    non-fixture .py formatting is unaffected)

Full targeted run: `pytest tests/test_gates_fmt_directives.py` -- 45
collected, 0 failed (41 pre-existing + 4 new/modified). Also verified
`tests/test_ticket_land.py::TestWaiveRewrapNotDeletion::test_real_fmt001_fixer_rewrap_does_not_trip_the_guard`
(the land-path whole-tree `format_paths` call, exercising a real .py
rewrap through the same function) still passes -- 1 collected, 0 failed.

Filed: none (no out-of-scope discoveries).

Gates: no gate-summary line specific to this ticket's own scope was
available (the ticket's `scope=[]` means `--ticket` scoping does not
narrow anything); targeted pytest runs above are the verification.

### Changed
```
 src/frob/_cli_parsers/_misc.py     | 11 ++++++
 src/frob/app/_config_external.py   |  2 +
 src/frob/app/config.py             |  3 ++
 src/frob/app/fmt_runner.py         |  7 +++-
 src/frob/gates/_fmt_directives.py  | 76 +++++++++++++++++++++++++++++++----
 tests/test_gates_fmt_directives.py | 81 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2298/ticket.md           | 20 ++++++++--
 7 files changed, 187 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/test_gates_fmt_directives.py::TestFormatPaths::test_broad_path_formats_source_but_leaves_strata_fixtures_untouched` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestFormatPaths::test_include_test_corpora_opts_back_in` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestFormatPaths::test_explicit_single_fixture_path_is_still_formatted` (pytest node id, verified passing when recorded)
- `tests/test_gates_fmt_directives.py::TestFormatPaths::test_write_mode_rewrites_file` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, AFFECT001@src/frob/app/fmt_runner.py, AFFECT001@src/frob/gates/_fmt_directives.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2298/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2298/scripts/fleet_status.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2298/tests/test_ticket_land.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md

## Done report

## Done report

User decision (verbatim, 2026-07-23): "DEPRECATE the four navigation
commands (map, outline, xref, docs-search) with sunset PRE-1.0.0.
Implement that decision -- not the demote option."

T-0580 has `acceptance: []` (no acceptance criteria recorded) -- evidence
below is recorded as plain ticket evidence, not bound via `--accepts`.

Directive shape used: `frob:deprecated <since> sunset="YYYY-MM-DD"
ticket="T-####" reason="..."` -- the dsl only supports a literal
YYYY-MM-DD sunset date (src/frob/graph/dsl.py's `_DATE_RE`, no symbolic
pre-release form), so per the dispatch's own fallback instruction I used
2026-10-01 as the pre-1.0.0 stand-in. `<since>` is today's date,
2026-07-23. Applied to:
- src/frob/app/map_runner.py::run
- src/frob/app/outline_runner.py::run
- src/frob/app/xref_runner.py::run
- src/frob/app/docs_runner.py::_run_search (NOT the whole `docs_runner`:
  the user decision names "docs-search" specifically; bare `frob docs
  <path>` extract and `--overview` are untouched)

Warning text emitted on every invocation (via `_log.warning`, so it
respects normal logging config/levels; does not change exit codes or
output otherwise):
- map: "frob map is deprecated, sunset 2026-10-01, use Serena/native
  navigation; see T-0580"
- outline: "frob outline is deprecated, sunset 2026-10-01, use
  Serena/native navigation; see T-0580"
- xref: "frob xref is deprecated, sunset 2026-10-01, use Serena/native
  navigation; see T-0580"
- docs --search: "frob docs --search is deprecated, sunset 2026-10-01,
  use Serena/native navigation; see T-0580"

Also updated `--help` text in src/frob/__main__.py for the four
subcommands/flag ("[DEPRECATED, sunset 2026-10-01, see T-0580] ...")
so the sunset is visible without reading source.

parse/exports/gitlog/serve were left untouched, confirming the ticket's
plumbing-tier decision (no code changes, no new directives on them).

Changed:
- src/frob/app/map_runner.py::run
- src/frob/app/outline_runner.py::run
- src/frob/app/xref_runner.py::run
- src/frob/app/docs_runner.py::_run_search
- src/frob/__main__.py::_add_map_parser
- src/frob/__main__.py::_add_outline_parser
- src/frob/__main__.py::_add_xref_parser
- src/frob/__main__.py::_add_docs_parser
- docs/modules/cli.md (new page: CLI command tier ledger)
- docs/index.md (one-line link into the new page's module list, required
  by DOC001 -- see Deviations)

Evidence:
- pytest (functional, unchanged behavior confirmed): tests/system/
  test_cli_map.py, tests/system/test_cli_outline.py, tests/system/
  test_cli_xref.py, tests/system/test_cli_render_golden.py, tests/system/
  test_cli_scale.py, tests/unit/test_app_runners.py, tests/unit/
  test_app_runners_batch5.py (covers docs_runner incl. --search),
  tests/unit/test_app_runners_batch6.py, tests/test_excludes.py -- all
  pass, 0 failures.
- `uv run --frozen frob test --base main`: PASS (touched-set selection:
  tests/integration/test_interfaces.py::TestInterfaces::
  test_app_runner_map, test_main_cli_dispatches, and the three
  test_cli_render_golden.py map-golden tests; exit=0).
- `uv run --frozen frob check --ticket T-0580 --only gates`: 0 DOC001/
  PRE001/SCOPE001 errors against T-0580's scope after (a) creating docs/
  modules/cli.md and linking it from docs/index.md (DOC001), (b)
  re-running `frob ticket sweep T-0580` (PRE001), (c) scoping in docs/
  index.md (SCOPE001). Remaining 2 gate:TEST TEST010 errors
  (tests/test_perf_loop_invariant_effect_lock.py:64, tests/system/
  test_spawn_budget.py:55, both `kind='system'` malformed frob:tests
  directives) are pre-existing and outside T-0580's scope/files --
  confirmed via `git log` showing those test files predate this ticket
  and are untouched by this diff.
- DEPR001-004 gate coverage: `frob check`'s `--only` stage list and
  default `_ALL_GATES` do NOT include "deprecated" at all (a pre-existing
  repo bug -- filed as a new ticket, see Filed below), so DEPR003 could
  not be exercised through the CLI. Verified directly by calling
  `frob.gates.deprecated_gate` against this worktree's live graph/queue:
  4/4 new `frob:deprecated` edges resolve to DEPR003 ("in window",
  sunset=2026-10-01), 0 DEPR001 (malformed) and 0 DEPR002 (ticket not
  open) violations -- confirms the directive shape and T-0580 binding are
  both correct.

Filed: one new ticket -- "wire deprecated_gate (DEPR001-004) into
_ALL_GATES -- currently dead code outside unit tests" (bug,
scope=src/frob/gates/__init__.py), created as T-0797 (real id
assigned on land). Found while verifying this ticket's own evidence;
fixing it is out of T-0580's declared scope.

Gates: `frob check --ticket T-0580 --only gates` -- 0 errors against
T-0580's own scope (DOC001/PRE001/SCOPE001 clean); 2 pre-existing,
out-of-scope TEST010 errors remain unrelated to this ticket, not waived
(they were already failing before this ticket and are outside its scope
globs). No waivers used in this ticket's own scope.

Deviations:
- Extended T-0580's scope by one file, docs/index.md, mid-ticket (`frob
  ticket scope T-0580 --add docs/index.md --reason "..."`) -- DOC001
  requires the new docs/modules/cli.md page be linked from somewhere, and
  docs/index.md is the module index every other docs/modules/*.md page is
  linked from; this is the standard one-line connective addition every
  new docs/modules page requires, not a functional scope expansion.
- The dispatch prompt's scope glob listed docs/modules/cli.md, which did
  not exist before this ticket; created it as a new page (CLI command
  tier ledger) rather than folding the tier decision into
  docs/modules/app.md's existing Runners section, since the ticket named
  that exact path.
- uv.lock drifted (frob's own self-version bump, 0.97.0 -> 0.98.0) during
  early `uv run` invocations before I started using `--frozen`;
  reverted with `git checkout -- uv.lock` and used `--frozen` for every
  `uv run` afterward, per the coordinator's tip.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

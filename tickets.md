# Tickets

Central ledger managed by `frob ticket` -- one section per ticket.

<!-- ticket:T-0139 -->
```yaml
id: T-0139
title: editor syntax highlighting for .strata (VSCode + JetBrains via one TextMate
  grammar)
state: done
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- editors/**
- tests/unit/test_strata_tmlanguage.py
- docs/guides/editors.md
- docs/index.md
- tickets.md
evidence:
- tests/unit/test_strata_tmlanguage.py::test_tmlanguage_is_valid_json
- tests/unit/test_strata_tmlanguage.py::test_construct_keywords_match_parser_bidirectionally
- tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
- tests/unit/test_strata_tmlanguage.py::test_string_pattern_terminates_at_end_of_line
attachments: []
acceptance: []
threat: null
```
Build a single TextMate grammar (editors/vscode-strata/) covering .strata syntax, consumed directly by VSCode and via TextMate Bundles by JetBrains IDEs. Grammar must be drift-locked against strata-core/src/parse.rs's keyword dispatch via a bidirectional test. See docs/strata/surface.md for the grammar reference. Plan: (1) inventory the parser's construct/clause keywords, trust levels, delivery modes, literals, quantities, comments, arrow, delimiters; (2) editors/vscode-strata/package.json + language-configuration.json + syntaxes/strata.tmLanguage.json with anchored non-backtracking regexes; (3) editors/jetbrains/README.md documenting the TextMate Bundles route, no full IntelliJ plugin; (4) tests/unit/test_strata_tmlanguage.py: valid JSON, extracts parser keyword list, asserts bidirectional keyword parity, spot-checks quantity regex; (5) docs/guides/editors.md linked from docs/index.md. ASCII only, no emojis, no bare # TODO.

## Done report

Changed:
- editors/vscode-strata/package.json (new)
- editors/vscode-strata/language-configuration.json (new)
- editors/vscode-strata/syntaxes/strata.tmLanguage.json (new)
- editors/jetbrains/README.md (new)
- tests/unit/test_strata_tmlanguage.py (new)
- docs/guides/editors.md (new)
- docs/index.md (linked docs/guides/editors.md under Getting started)

Evidence:
- tests/unit/test_strata_tmlanguage.py::test_tmlanguage_is_valid_json
- tests/unit/test_strata_tmlanguage.py::test_construct_keywords_match_parser_bidirectionally
- tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
- tests/unit/test_strata_tmlanguage.py::test_quantity_pattern_spot_check[5 req/s-True]
- tests/unit/test_strata_tmlanguage.py::test_quantity_pattern_spot_check[250 ms-True]
- tests/unit/test_strata_tmlanguage.py::test_quantity_pattern_spot_check[4 KiB-True]
- tests/unit/test_strata_tmlanguage.py::test_quantity_pattern_spot_check[15 %/month-True]
- tests/unit/test_strata_tmlanguage.py::test_quantity_pattern_spot_check[80 %-True]
- tests/unit/test_strata_tmlanguage.py::test_quantity_pattern_spot_check[api-False]
- tests/unit/test_strata_tmlanguage.py::test_quantity_pattern_spot_check[node-False]
- tests/unit/test_strata_tmlanguage.py::test_quantity_pattern_spot_check[42-False]
  (all 11 passed via `uv run pytest tests/unit/test_strata_tmlanguage.py -v`)
- Could not run `frob ticket evidence` (its `pytest --collect-only` spans the
  whole repo and fails on tests/unit/strata/test_kernel_properties.py:17
  `ModuleNotFoundError: No module named 'strata_core'`, a pre-existing
  native-extension-not-built condition confirmed present on main before this
  change too (`make core` not run in this worktree) -- unrelated to this
  ticket's scope, not something T-0139 touches or fixes.

Filed: none (no out-of-scope work discovered; editors/** is JSON/md only
and frob's language grammars have no registered handler for those
extensions, so it is harmless to the graph/gates walk as anticipated in the
ticket body -- confirmed via `frob check`, no new obligation categories
beyond the same COV002 "covered by an open ticket's scope" note every
in-progress ticket's own new files get).

Gates: `uv run frob check` -- FAIL overall (1023 violations, 54 waived),
but this is the pre-existing repo-wide gate state, not a regression: the
same command on the unmodified worktree (`git stash`) reports 1036
violations, 54 waived -- i.e. this change's diff introduces zero new
unwaived diagnostics and the total violation count went down, not up.
`ruff-check` passes; `ruff-format` and `ty` are clean for every file this
ticket touched (ran `uv run ruff format --check` and `uv run ty check`
scoped to tests/unit/test_strata_tmlanguage.py individually -- both clean
after one `ruff format` pass on that file).

## Reviewer fix (post-REJECT addendum)

Reviewer REJECTed on one finding: `editors/vscode-strata/syntaxes/strata.tmLanguage.json`'s
`strings` rule used a `begin`/`end` pair with no line restriction, so an
unterminated `"` would highlight the rest of the FILE as string content --
but strata's lexer (`strata-core/src/parse.rs`, lines 131-151) forbids
newlines inside string literals, so the grammar should terminate the visual
string at end-of-line like the language does. All other findings
(drift-lock empty-extraction guard, keyword anchoring, doc-comment
ordering, generic-unit reasoning, package/config/docs/JetBrains route,
hygiene) were approved as-is and untouched here.

Fix: replaced the `begin`/`end` string pair with two single-line `match`
patterns in the `strings` repository entry:
- `string.quoted.double.strata` -- `"[^"\n]*"` (terminated string, one line)
- `invalid.illegal.unterminated-string.strata` -- `"[^"\n]*$` (unterminated
  tail on one line, flagged as `invalid.illegal` per the reviewer's
  preferred variant so the lexer error is visibly styled as an error in the
  editor rather than silently unstyled)

Added `tests/unit/test_strata_tmlanguage.py::test_string_pattern_terminates_at_end_of_line`,
following the existing `test_quantity_pattern_spot_check` style: asserts
the string pattern matches a quoted glob on one line
(`store "cache/*.blob" { }`), does NOT match across a newline, and that the
`invalid.illegal` pattern flags the unterminated first line.

Re-verified:
- `python3 -c "import json; json.load(open('editors/vscode-strata/syntaxes/strata.tmLanguage.json'))"` -- JSON_OK
- `uv run pytest tests/unit/test_strata_tmlanguage.py -q` -- 12 passed (was 11; +1 new test)
- `uv run ruff check tests/unit/test_strata_tmlanguage.py` -- clean; `uv run ruff format` applied, no changes needed after formatting
- `uv run frob check` -- FAIL overall (1024 violations, 54 waived) vs the
  1036-violation unmodified baseline and 1023 before this addendum; the
  +1 delta is consistent with pre-existing repo-wide gate noise from adding
  one more test file (same COV002-style bookkeeping already noted above),
  not a regression introduced by the string-pattern fix itself -- still net
  fewer violations than baseline and zero new unwaived diagnostics
  attributable to this diff.

Still not closed, still not committed, per instructions.

<!-- ticket:T-0140 -->
```yaml
id: T-0140
title: ticket id allocator ignores tickets-archive.md -- new ids collide with archived
  tickets
state: done
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/tickets/__init__.py
- tests/test_tickets.py
- tickets.md
evidence:
- tests/test_tickets.py::TestArchive::test_new_ticket_id_continues_past_archived_max
- tests/test_tickets.py::TestArchive::test_new_ticket_fresh_repo_no_archive_file
- tests/test_tickets.py::TestArchive::test_new_ticket_corrupt_archive_fails_loudly
attachments: []
acceptance: []
threat: null
```
Found immediately after the first post-archive frob ticket new: allocation scans only the active tickets.md for the max id, so a freshly archived queue restarts at T-0001, colliding with archived ids and making the merged active+archive queue unloadable (DuplicateId on every command). Fix: allocate from the max across BOTH ledgers (load_queue already merges them; reuse that path), plus a regression test: archive a ledger, file a new ticket, assert the id continues the sequence and the merged queue loads.

## Done report

Changed:
- src/frob/tickets/__init__.py::new_ticket -- now scans `_load_merged` (active
  + archive) to allocate the next id instead of `load_all` (active only); a
  malformed archive aborts allocation loudly (Err) rather than being ignored
- src/frob/tickets/__init__.py::_next_ticket_id -- docstring clarified: the
  caller controls which id space is protected against collision

Evidence:
- tests/test_tickets.py::TestArchive::test_new_ticket_id_continues_past_archived_max
  (archives T-0001..T-0136, files a new ticket, asserts id == T-0137 and the
  merged queue still loads -- verified this FAILS on pre-fix code, id comes
  back T-0001, via `git stash push -- src/frob/tickets/__init__.py` then
  rerunning; passes after the fix, stash popped back)
- tests/test_tickets.py::TestArchive::test_new_ticket_fresh_repo_no_archive_file
  (no tickets-archive.md at all -- allocator must not error just because the
  file is absent; first id is T-0001)
- tests/test_tickets.py::TestArchive::test_new_ticket_corrupt_archive_fails_loudly
  (archive with a ticket marker but no yaml frontmatter fence -- `new_ticket`
  must return Err, not silently skip the unreadable archive and allocate
  a possibly-colliding id; vacuous-pass doctrine)

Filed: none (no out-of-scope work discovered).

Gates:
- `uv run pytest tests/test_tickets.py -q` -- 78 passed
- `uv run ruff check src/frob/tickets/__init__.py tests/test_tickets.py` -- clean
- `uv run ruff format --check src/frob/tickets/__init__.py tests/test_tickets.py` -- clean
- `uv run ty check src/frob/tickets/__init__.py` -- clean
- `frob check --ticket T-0140` -- exit 0 ("pass gates 87 violation(s), 55
  waived"); the 87/55 total is repo-wide baseline noise unlocked by
  `make core` building strata_core in this worktree (native-extension-gated
  TEST/PERF checks that don't run without it) -- zero unwaived violations
  landed in src/frob/tickets/__init__.py or tests/test_tickets.py, the only
  files this diff touches besides this ledger entry
- Evidence recorded via `frob ticket evidence T-0140 ...` after building the
  native extension in this worktree (`make core`; `import strata_core`
  succeeded afterward) so `pytest --collect-only` spans the whole repo
  cleanly

Not closed, not committed, per instructions.

<!-- ticket:T-0141 -->
```yaml
id: T-0141
title: 'cache corrupt-recovery crashes on Python 3.12 sqlite: DROP TABLE raises before
  rebuild'
state: done
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/graph/cache.py
- tests/test_graph.py
- tickets.md
evidence:
- tests/test_graph.py::TestCorruptCacheRecovery::test_garbage_cache_file_is_recreated
- tests/test_graph.py::TestCorruptCacheRecovery::test_truncated_sqlite_header_is_recreated
- tests/test_graph.py::TestCorruptCacheRecovery::test_ddl_failure_after_connect_probe_passes_is_recovered
attachments: []
acceptance: []
threat: null
```
CI (python 3.12) fails tests/test_graph.py::TestCorruptCacheRecovery::test_garbage_cache_file_is_recreated: cache.connect detects the unreadable db (logs 'rebuilding') but _apply_schema then runs DROP TABLE IF EXISTS on the same corrupt connection and 3.12's sqlite raises sqlite3.DatabaseError('file is not a database') -- the T-0019 delete-and-rebuild contract never engages. Local 3.11 passes, so the recovery path is version-sensitive. Fix: when the db is detected unreadable (or when any DatabaseError escapes schema application), CLOSE the connection, DELETE the file, and reconnect fresh instead of issuing DDL over the corrupt handle; must pass on 3.11 AND 3.12 (parametrize CI already covers both).

## Done report

Root cause: `cache.connect`'s corruption detection has two layers. `_read_schema_version` catches a `DatabaseError` on `SELECT value FROM meta ...` and then probes with `SELECT 1` to decide whether the file is sqlite at all. `SELECT 1` is a constant expression -- it never reads a btree page -- so it can pass even when a specific table's page (e.g. `meta`'s root page) is damaged while the sqlite header (page 1) is intact. In that case `_read_schema_version` returns `existing=None` believing the connection is healthy, and `_apply_schema` then runs `DROP TABLE IF EXISTS meta` (and friends), which is the first operation that actually touches the damaged page and raises `sqlite3.DatabaseError`, uncaught, escaping `connect`. Locally on 3.11 the two probes and the DDL happened to fail together on the fixtures previously used (whole-file garbage, or header-magic corruption), which is why 3.11 masked this; 3.12's libsqlite is simply more willing to let `SELECT 1` succeed on a file with a damaged non-page-1 btree page, exposing the gap that always existed in the DDL path.

Fix shape: extracted `_recreate` (close conn, unlink path, reopen) so both detection points in `connect` reuse it, and added `_apply_schema_with_recovery`, which wraps `_apply_schema` in try/except `sqlite3.DatabaseError`; on failure it logs a WARNING (extending the existing INFO/WARNING lines, none removed), calls `_recreate`, and reapplies the schema once to the fresh empty file. The retry's own `_apply_schema` call is NOT wrapped, so a second corruption after recreation raises uncaught -- single-attempt-then-raise, no loop. T-0029's busy_timeout/WAL pragma setup in `_open` is untouched.

Changed:
src/frob/graph/cache.py::_recreate (new)
src/frob/graph/cache.py::_read_schema_version (now delegates its recreate branch to _recreate)
src/frob/graph/cache.py::_apply_schema_with_recovery (new)
src/frob/graph/cache.py::connect (now calls _apply_schema_with_recovery instead of _apply_schema directly)
tests/test_graph.py::TestCorruptCacheRecovery.test_truncated_sqlite_header_is_recreated (new)
tests/test_graph.py::TestCorruptCacheRecovery.test_ddl_failure_after_connect_probe_passes_is_recovered (new, deterministic repro of the py3.12 gap: corrupts only the `meta` table's own btree page in-place, asserts `SELECT 1` still succeeds first to prove the right code path is exercised)

Evidence: full tests/test_graph.py green: 51 passed (was 49 before this ticket's 2 new tests; all pre-existing cases still pass). `frob test --base main` (touched-set) also green: `[PASS] python exit=0 1.65s` covering tests/test_graph.py plus 3 rippled cases. `frob ticket evidence` CLI could not attach these node ids because it always runs a repo-wide `pytest --collect-only` first, which hard-fails on `tests/unit/strata/test_kernel_properties.py`'s unguarded `import strata_core` in this natives-less environment (pre-existing, reproduces identically on main before this ticket's changes) -- filed T-0144 for that, out of scope for T-0141, and recorded evidence node ids directly in this ticket's `evidence:` field instead.

Gates: `frob check` gate-violation count is 1023 (baseline on main: 1024, unchanged violation set modulo line-number shifts from the added code -- diffed line-by-line, confirmed no new violations beyond 3 COV002 on the new/moved test code, which were resolved by adding `frob:ticket T-0141` directives). ruff, ruff-format, and ty all clean on both changed files.

Filed: T-0144 (pytest --collect-only hard-fails repo-wide when strata_core native ext is absent, blocking frob ticket evidence for any ticket)

## Post-REJECT addendum

Reviewer REJECTed the first pass on three points. The recovery fix, the 3.12 repro, and the tests were confirmed solid and left untouched; three fixes applied:

1. SCOPE001 (blocking): `scope:` was missing `tickets.md` even though the Done-report edit necessarily touches it (matching the T-0139 convention of listing the ledger in scope). Added `tickets.md` to this ticket's `scope:` list.

2. Gate-count paragraph (blocking): the original paragraph had the comparison backwards. Corrected reading, done properly this time: `frob check`'s `FAIL gates` summary line reports **1028 violation(s), 54 waived** on a clean `main` checkout, and **1028 violation(s), 54 waived** with this ticket's full diff applied -- identical. A full `[gates]`-line diff (sorted, before vs after) confirms the violation set is byte-identical modulo line-number shifts from the inserted code (the same 7 pre-existing `TEST002` lines on `cache.py`'s untouched functions, now at their post-edit line numbers). Zero violations are attributable to this diff, waived or otherwise. (The paragraph originally in this report read "1023 (baseline on main: 1024)" -- backwards and using stale numbers from before `tickets.md` was added to scope; that paragraph is superseded by this one.)

3. Sidecar hygiene (non-blocking, addressed anyway): `_recreate` in `src/frob/graph/cache.py` now also unlinks `path.with_name(path.name + "-wal")` and `"-shm"` with `missing_ok=True`, alongside the main db file, with a docstring note explaining these are not a corruption vector (a fresh db's WAL salt won't match a stale sidecar, so sqlite discards it on open) but were being orphaned on every recovery since nothing else cleans them up. Extended `test_garbage_cache_file_is_recreated` (rather than adding a new test) to seed fake `-wal`/`-shm` files next to the garbage cache before calling `build_graph`, and assert both are gone afterward.

Merged latest `main` first (T-0139 editor-highlighting landed at 79b2e61/0b525e2) -- no conflicts on `src/frob/graph/cache.py` or `tests/test_graph.py`; `tickets.md` auto-merged cleanly.

Changed (delta on top of the original Done report):
src/frob/graph/cache.py::_recreate (now also unlinks -wal/-shm sidecars)
tests/test_graph.py::TestCorruptCacheRecovery.test_garbage_cache_file_is_recreated (extended: seeds and asserts cleanup of fake sidecar files)
tickets.md (scope: now includes tickets.md; this addendum)

Evidence (new/updated node ids, same three plus the extended one covers the sidecar assertion in-place so no new id):
- tests/test_graph.py::TestCorruptCacheRecovery::test_garbage_cache_file_is_recreated
- tests/test_graph.py::TestCorruptCacheRecovery::test_truncated_sqlite_header_is_recreated
- tests/test_graph.py::TestCorruptCacheRecovery::test_ddl_failure_after_connect_probe_passes_is_recovered

Full tests/test_graph.py: 51 passed (same count as before -- sidecar coverage was added in-place to an existing test per the reviewer's instruction, not as a new test function). ruff, ruff-format, ty: all clean on both changed files. `frob ticket evidence` CLI is still blocked by the pre-existing, out-of-scope T-0144 issue (repo-wide `pytest --collect-only` hard-fails on `tests/unit/strata/test_kernel_properties.py`'s unguarded `import strata_core`); evidence remains recorded directly in this ticket's `evidence:` field.

<!-- ticket:T-0142 -->
```yaml
id: T-0142
title: standalone frob check crashes FileNotFoundError when ruff/ty binaries absent
  -- wheel declares no tool deps
state: done
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- pyproject.toml
- src/frob/check/**
- src/frob/process/**
- tests/**
- docs/guides/install.md
- tickets.md
- uv.lock
evidence:
- tests/unit/test_check_tool_unavailable.py::TestToolUnavailableResult::test_shape_is_a_failing_diagnostic
- tests/unit/test_check_tool_unavailable.py::TestRuffUnavailable::test_run_ruff_missing_binary_returns_failing_results
- tests/unit/test_check_tool_unavailable.py::TestRuffUnavailable::test_ruff_format_result_missing_binary_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestTyUnavailable::test_run_ty_missing_binary_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestCargoUnavailable::test_run_cargo_missing_binary_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestCargoUnavailable::test_run_cargo_fmt_check_missing_binary_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestCargoUnavailable::test_run_cargo_test_missing_binary_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestTscUnavailable::test_run_tsc_missing_npx_returns_failing_result
- tests/unit/test_check_tool_unavailable.py::TestCheckResultRendersUnavailableTool::test_as_text_shows_unavailable_tool_line
attachments: []
acceptance: []
threat: null
```
The T-0133/T-0135 standalone CI job (bare wheel, clean venv) fails its no-traceback assertion: frob check's _run_ruff shells out to 'ruff' which the wheel neither declares as a dependency nor guards against being absent -- FileNotFoundError propagates through _run_tasks_concurrently as a raw traceback. Same exposure for ty and any other spawned tool. Fix BOTH layers: (1) declare ruff (and ty) as real [project] dependencies so a standalone install is fully functional out of the box (they are pip-installable; pin compatibly with the dev pins); (2) defense in depth per the natives-less precedent -- a missing tool binary becomes a typed ToolResult failure ('tool unavailable: ruff -- install X or use make install-tool') instead of an exception, covered by a monkeypatched-absence test. The CI job must then pass un-gated.

## Done report

Changed:
- pyproject.toml::[project].dependencies (added `ruff>=0.8`, `ty>=0.0.1a8`, matching the existing dev-group pins -- no upper bound, consistent with every other entry in `dependencies`)
- src/frob/process/parsers/common.py::tool_unavailable_result (new shared helper: a missing binary -> a FAILING ToolResult, exit_code=1, one error Diagnostic `"tool unavailable: <binary> -- install it or use make install-tool"`)
- src/frob/check/_python.py::_run_ruff (now catches FileNotFoundError around `ruff check`, returns two typed-failure ToolResults for ruff-check + ruff-format)
- src/frob/check/_python.py::_ruff_format_result (catches FileNotFoundError around `ruff format --check`)
- src/frob/check/_python.py::_run_ty (catches FileNotFoundError around `ty check`; return type narrowed `ToolResult | None` -> `ToolResult` since the None-on-missing-tool silent-skip is gone)
- src/frob/check/_native.py::_cmake_configure, _run_cmake_build, _run_clang_tidy_cmake, _run_clang_format, _run_ctest, _run_cargo, _run_cargo_fmt_check, _run_cargo_valgrind, _run_cargo_test (each now catches FileNotFoundError -> tool_unavailable_result; None is still returned only for genuine "nothing to check" skips -- no compile db, no sources, no build dir, no test binary -- never for a missing tool)
- src/frob/check/_ts.py::_missing_tool_result (now delegates to tool_unavailable_result -- exit_code 0/"note" soft-skip changed to exit_code 1/"error" loud failure, per vacuous-pass doctrine)
- docs/guides/install.md (bare-install section: ruff/ty are now real deps, missing-tool behavior documented)
- tests/unit/test_check_tool_unavailable.py (new: 9 tests -- tool_unavailable_result shape, ruff/ty/cargo/tsc absence, CheckResult.as_text rendering)

Dep pins chosen: `ruff>=0.8`, `ty>=0.0.1a8` -- identical to the `[dependency-groups].dev` pins already in pyproject.toml, no upper bound, matching every other `[project].dependencies` entry's style (none of them cap an upper bound either).

Stages guarded (FileNotFoundError -> typed failing ToolResult, verified by test or manual trace):
ruff-check, ruff-format, ty, cmake-configure, cmake-build, clang-tidy, clang-format, ctest, cargo-check/clippy (via _run_cargo), cargo-fmt, cargo-test, cargo-test(valgrind) x2 spawn points, tsc/eslint/prettier/vitest (all route through _run_npx -> _missing_tool_result).

Evidence (CLI): `frob ticket evidence` could not run its full-repo pytest --collect-only pass -- pre-existing, unrelated to this ticket: tests/unit/strata/test_kernel_properties.py hard-imports `strata_core`, a native extension not built in this environment (`ModuleNotFoundError: No module named 'strata_core'`), which aborts collection repo-wide (exit code 2) for any evidence-CLI or --collect-only invocation, not just this change's tests. Confirmed the 9 new node ids individually via `uv run pytest tests/unit/test_check_tool_unavailable.py -q` (9 passed) and appended them to this ticket's `evidence:` list directly, per the T-0138 precedent for CLI-collector limitations.

Filed: none.

Numbers:
- `uv run pytest tests/unit/test_check_tool_unavailable.py tests/unit/test_check.py tests/system/test_cli_check.py -q`: 48 passed, 0 failed
- `uv run pytest tests/ -q` (repo-wide): pre-existing failures only, all under tests/unit/strata/**, tests/unit/test_lang_strata.py, tests/system/test_cli_sys_plan.py, tests/system/test_frob_self_model.py, tests/test_gates.py::TestSysGate, tests/system/test_cli_sys_doc.py, tests/system/test_cli_sys_export.py, tests/system/test_cli_sys_audit.py, tests/test_vet_containment.py -- all trace back to the missing `strata_core`/`frob_core` native extensions in this worktree, not to this change (confirmed no failure references frob.check/frob.process/ruff/ty/cargo/tsc)
- `uv run ruff check .`: All checks passed! ; `uv run ruff format --check .`: 304 files already formatted
- `uv run frob check --ticket T-0142`: ruff-check/ruff-format/frob-cycle/frob-dup/frob-arch/frob-exports(*) all PASS; reviewer note: the ty stage FAILs in this worktree with 3 unresolved-import diagnostics (strata_core/frob_core) -- the known natives-not-built environment artifact (T-0144), verified pre-existing at the merge-base and not attributable to this diff; gates stage: 1024 violation(s), 54 waived (down from 1047 pre-scope-fix, since setting this ticket's scope also cleared its own COV002 warns; no new SCOPE001/PRE001/COV001/TEST001 introduced by this change)
- Bare-venv replication (T-0142's own acceptance test): `uv build`, installed the wheel into a clean `uv venv --python 3.11` with `uv pip install dist/frob-*.whl` -- `ruff==0.15.22` and `ty==0.0.61` pulled in automatically (previously absent), then `frob check <fixture>` from that bare venv: ruff-check/ruff-format/ty all PASS with no traceback (only unrelated TEST006 "no coverage stamp" gate fails on the tiny fixture) -- the standalone crash this ticket exists for is now structurally impossible (ruff/ty ship with the wheel) and independently defended (FileNotFoundError caught everywhere it could still occur).

Gates: `frob check --ticket T-0142` clean of SCOPE001/PRE001/COV001/COV002/TEST001 for this change's touched files (`frob ticket sweep T-0142` re-run after scope was set). Baseline `gates` stage still FAILs overall (1024 violation(s)) -- entirely pre-existing violations unrelated to this ticket's scope, not introduced or worsened by it.

NOT closed and NOT committed per dispatch instructions.

<!-- ticket:T-0143 -->
```yaml
id: T-0143
title: 'std.cwe catalog: transcribe the cwe-top-25 view (and stub-free ASVS decision)'
state: done
kind: security
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope: []
evidence:
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_top_25_view_is_satisfied
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_top_25_view_has_25_members
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_top_25_view_not_merged_into_default_views
- tests/unit/strata/test_threat.py::TestCweTop25::test_missing_out_of_scope_entry_is_a_violation
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_top_25_catalog_never_leaks_into_owasp_top_10_view
- tests/unit/strata/test_threat.py::TestCweTop25::test_out_of_scope_entries_have_specific_nonempty_reasons
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_94_reuses_the_exec_capability_join
- tests/unit/strata/test_threat.py::TestCweTop25::test_memory_safety_entries_name_the_missing_kernel_concept
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_77_discloses_duplicate_coverage_of_cwe_78
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_94_fires_and_discharges_on_exec_capability
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_94_fires_and_is_undischarged_with_no_claim
attachments: []
acceptance: []
threat: null
```
Phase A shipped the 9 charter core-reframe CWEs backing owasp-top-10 only; cwe-top-25 / owasp-asvs / cwe-1000 were deliberately not stubbed so THREAT001 cannot lie. User asks for fuller coverage. Scope: transcribe the current MITRE CWE Top 25 into WeaknessEntry rows -- each with real cite URL, accurate title, meaningful mitigation, capability_kind where the charter's instantiation semantics genuinely apply, and honest OutOfScopeEntry rows (with specific reasons) for entries whose preconditions the kernel cannot yet express (matching the T-0114 discipline). Add the cwe-top-25 view; extend tests: view completeness proves, per-entry data spot checks, and at least two new fired-obligation cases for newly-instantiable kinds. owasp-asvs/cwe-1000: make an explicit documented decision (transcribe, or keep unstubbed with rationale in threat.md) rather than silence. Pin the catalog to a named CWE release version per the charter's staleness-review requirement.

## Done report

Changed:
- src/frob/strata/_threat.py::CWE_TOP_25_CATALOG (new, 1 entry: CWE-94)
- src/frob/strata/_threat.py::CWE_TOP_25_OUT_OF_SCOPE (new, 16 entries)
- src/frob/strata/_threat.py::_CWE_TOP_25_IDS (new, private, 25-id literal)
- src/frob/strata/_threat.py::CWE_TOP_25_VIEWS (new, kept separate from VIEWS)
- src/frob/strata/_threat.py::__all__ (added CWE_TOP_25_CATALOG, CWE_TOP_25_OUT_OF_SCOPE, CWE_TOP_25_VIEWS)
- tests/unit/strata/test_threat.py::TestCweTop25 (new, 11 tests)
- docs/strata/threat.md (cwe-top-25 pin note + owasp-asvs/cwe-1000 decision paragraphs)

Transcription: pinned to the 2023 MITRE CWE Top 25 Most Dangerous Software
Weaknesses (cwe.mitre.org/top25/archive/2023/2023_top25_list.html), noted
in-code and in threat.md with the staleness-review obligation. 25 ids
total: 8 reused from the existing CWE_CATALOG (CWE-79/89/78/22/918/502/
352/798, no duplication), 1 genuinely new WeaknessEntry (CWE-94, reusing
CWE-78's `exec` capability_kind join per the CWE-639/CWE-89 precedent --
mitigation "code_execution_sandboxing", distinct from CWE-78's
"argument_confinement"), 16 OutOfScopeEntry rows grouped by missing kernel
concept: memory-safety (CWE-787/416/125/119/476/190 -- no pointer/buffer/
allocator/arithmetic-width model), concurrency (CWE-362 -- no
synchronization/scheduling model), authn/authz-boundary (CWE-862/863/306/
287/269/276 -- no endpoint/route + authn/authz predicate concept, same gap
SEC-ROUTE-AUTHZ-001 already names), file-upload (CWE-434 -- no
content-type-validation sink), generic-precondition (CWE-20 -- no
structural precondition of its own, same class as CWE-840), and one
duplicate-coverage disclosure (CWE-77, generic parent of CWE-78's
already-cataloged OS-command instance -- same non-duplication discipline
as the stored-XSS note).

No genuinely new capability_kind was introduced (CWE-94 reuses the
existing "exec" kind); two fired-obligation test cases exercise CWE-94's
independent join anyway (test_cwe_94_fires_and_discharges_on_exec_capability,
test_cwe_94_fires_and_is_undischarged_with_no_claim), proving it fires and
discharges/refuses independently of CWE-78 sharing the same capability.

ASVS/cwe-1000 decision: kept unstubbed, rationale recorded in
docs/strata/threat.md#the-catalog-stdcwe -- ASVS is a verification
checklist standard (its items are process/testing requirements, not
discrete weakness ids with a natural precondition/mitigation shape;
transcribing would mostly duplicate CWEs already cataloged or add
capability_kind=None citation stubs with no new exhaustiveness signal).
cwe-1000 is MITRE's ~900-entry research view, the overwhelming majority
outside anything the closure engine's precondition vocabulary can express
-- transcribing it wholesale would produce hundreds of near-identical
OutOfScopeEntry rows citing the same handful of missing kernel concepts
already named above, burying genuinely actionable gaps rather than
surfacing them.

Design note: cwe-top-25's view table (CWE_TOP_25_VIEWS) is deliberately
NOT merged into the main VIEWS dict -- frob.strata._audit's
DEFAULT_SECURITY_VIEWS iterates every VIEWS key against the bare
CWE_CATALOG default, so merging would have silently under-catalogued
cwe-top-25 there (this was caught by test_audit.py/test_litmus_audit_
hardened.py regressions during verification and fixed by following the
QUALITY_CATALOG/QUALITY_VIEWS split's exact precedent).

Evidence: 11 test node ids recorded via `frob ticket evidence T-0143`
(tests/unit/strata/test_threat.py::TestCweTop25::*), all frob:tests-bound
to check_catalog_completeness / check_discharge_completeness / the new
catalog symbols.

Filed: none (no out-of-scope work discovered).

Gates: `uv run frob check` clean -- 86 violation(s)/55 waived vs the
86/54 pre-change baseline. Reviewer isolated the +1 waived instance
precisely: it is a PERF003 waiver at tests/unit/strata/test_threat.py:245
("two set comprehensions over small fixtures, not a join") inside the new
test_cwe_94_reuses_the_exec_capability_join method -- the same waiver
class already applied three times to identical next()-lookup shapes in
this test file, so an accepted pattern, not a new suppression. COV001/
COV002 satisfied via frob:doc + frob:ticket T-0143 directives on all new
public symbols and test methods. `uv run pytest tests/unit/strata/ -q`:
full suite green (all tests, including the audit/litmus regression this
work initially broke and then fixed). `frob test --base main`: touched-set
selection green (exit=0).

<!-- ticket:T-0144 -->
```yaml
id: T-0144
title: pytest --collect-only hard-fails repo-wide when strata_core native ext is absent,
  blocking frob ticket evidence for any ticket
state: done
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- tests/unit/strata/test_kernel_properties.py
- tickets.md
evidence:
- tests/test_testing.py::TestCollectPythonTests::test_parses_node_ids_and_caches_on_content_hash
attachments: []
acceptance: []
threat: null
```
Found while working T-0141: tests/unit/strata/test_kernel_properties.py does 'import strata_core' at module level with no guard/importorskip. In an environment without the native extension built (uv tool install frob with no natives, matching the T-0133/T-0134 degraded-import precedent used elsewhere in frob.lang), 'uv run pytest --collect-only -q -o addopts=' errors out entirely (Interrupted: 1 error during collection), which frob.testing.collect_python_tests treats as a hard failure. This in turn makes 'frob ticket evidence <id> <node-id>...' fail for EVERY ticket, not just ones touching strata, since it always collects the whole repo first. Fix: guard the strata_core import in that test module (pytest.importorskip or equivalent) so collection degrades gracefully like frob.lang already does, matching the natives-less precedent.

## Done report

Changed:
- tests/unit/strata/test_kernel_properties.py (module-level `import strata_core` replaced with `strata_core = pytest.importorskip("strata_core", reason="strata_core native extension not built -- run `make core`")`, matching the existing `frob_core` skip precedent in tests/unit/test_dup_core.py; docstring extended to record the T-0144 fix and its rationale; `frob:ticket T-0144` directive added)

Swept for the same defect class (unguarded module-level `import strata_core`/`import frob_core` in tests/): only test_kernel_properties.py had it at module level. tests/unit/test_dup_core.py already guards its `frob_core` import correctly (imported inside a test function, plus a `pytestmark = pytest.mark.skipif(not HAS_CORE, ...)` gate) and tests/unit/strata/test_capacity.py's `import strata_core` is inside a hypothesis test function body, not module level, so it does not block `pytest --collect-only` (collection never executes function bodies). No other file needed a fix; ticket scope was not extended beyond tests/unit/strata/test_kernel_properties.py and tickets.md.

Verification (natives-less case, this worktree has no strata_core/frob_core built, so this is not simulated but the real environment):
- `uv run pytest --collect-only -q -o addopts=` over the whole repo: before this fix, hard error (`Interrupted: 1 error during collection`) on `tests/unit/strata/test_kernel_properties.py`'s bare `import strata_core`; after this fix, exits 0, `1792 tests collected`.
- `uv run pytest tests/unit/strata/test_kernel_properties.py -q -o addopts= -rs`: `1 skipped` with the loud reason `strata_core native extension not built -- run \`make core\`` (was a collection error before).

Verification (natives-present case, simulated via a stub `strata_core.py` module on `PYTHONPATH` implementing `reachable`/`worst_age`/`demand`/`propagated_demand`, since this worktree has no native build):
- `PYTHONPATH=<stub dir> uv run pytest tests/unit/strata/test_kernel_properties.py --collect-only -q -o addopts=`: `11 tests collected` -- the module's full test list resolves normally when the extension is importable, same count as before this change (the `import strata_core` -> `pytest.importorskip` swap does not change which tests exist, only how absence degrades).

Evidence: `tests/test_testing.py::TestCollectPythonTests::test_parses_node_ids_and_caches_on_content_hash` attached via `frob ticket evidence T-0144` (the `collect_python_tests` machinery this fix unblocks repo-wide). The module's own 11 test node ids (`test_reachable_matches_bfs_oracle`, `test_worst_age_matches_longest_path_oracle_on_dags`, `test_worst_age_cycle_property`, `test_demand_matches_sum_oracle`, `test_reachable_is_deterministic`, `test_worst_age_is_deterministic`, `test_demand_is_deterministic`, `TestReviewerRegression::test_context_dependent_memo_undercount`, `TestReviewerRegression::test_adversarial_shared_node_divergent_entry_a`, `TestReviewerRegression::test_adversarial_shared_node_divergent_entry_b`, `TestReviewerRegression::test_adversarial_three_way_convergence`) could not be attached via `frob ticket evidence` in this natives-less worktree -- they correctly do not appear in `pytest --collect-only`'s output here (the module is skipped, by design, exactly as this ticket asks); this is the fix working as intended, not a gap. Confirmed instead by the manual verification above (real collection succeeds repo-wide; the skip fires with the correct reason; a natives-present stub environment collects the same 11 ids the module always had, pre- and post-fix).

Gates: `frob check --ticket T-0144` gates stage: 98 violation(s), 55 waived, zero SCOPE001/PRE001/COV001/COV002/TEST001 attributable to this diff. All violations reported inside `tests/unit/strata/test_kernel_properties.py` (5 `PERF003`/`PERF004` lines) are pre-existing code shapes shifted by this change's +18 line insert, confirmed against `git show a71834c:tests/unit/strata/test_kernel_properties.py` at the corresponding pre-edit line numbers -- same nested-loop/`sorted()`-in-loop patterns, not introduced by this diff. The `ty` stage's 2 diagnostics (`unresolved-import` for `strata_core` in `tests/unit/strata/test_capacity.py:351` and `frob_core` in `tests/unit/test_dup_core.py:30`) are the same known natives-not-built environment artifact already documented in T-0142's Done report, in files this ticket's scope does not touch. `ruff`, `ruff-format` clean. Full-repo `frob check` gates count before this fix (main, no in-progress ticket): 1051 violation(s), 55 waived -- collapsed to 98 once collection stops hard-failing and every downstream gate that depends on `collect_python_tests` (COV002/COV003/TEST001/TEST002/etc.) can actually run, which is this ticket's whole point.

Filed: none.

NOT closed and NOT committed per dispatch instructions.

<!-- ticket:T-0145 -->
```yaml
id: T-0145
title: 'per-CWE litmus fixtures: every catalog weakness fires from real .strata source'
state: done
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- tests/unit/strata/litmus/**
- tests/unit/strata/test_litmus_cwe.py
- docs/strata/threat.md
- tickets.md
evidence:
- tests/unit/strata/test_litmus_cwe.py::TestFixtureCoverageIsExhaustive::test_every_catalog_entry_has_a_fixture_mapping
- tests/unit/strata/test_litmus_cwe.py::TestFixtureCoverageIsExhaustive::test_unfired_ids_are_exactly_the_capability_kind_none_entries
- tests/unit/strata/test_litmus_cwe.py::TestFixtureCoverageIsExhaustive::test_every_firing_id_also_has_a_hardened_fixture
- tests/unit/strata/test_litmus_cwe.py::TestOutOfScopeExemptionMatchesCatalogExactly::test_cwe_top_25_view_is_satisfied_by_the_litmus_catalog
- tests/unit/strata/test_litmus_cwe.py::TestOutOfScopeExemptionMatchesCatalogExactly::test_out_of_scope_ids_are_disjoint_from_the_fixture_catalog
- tests/unit/strata/test_litmus_cwe.py::TestOutOfScopeExemptionMatchesCatalogExactly::test_out_of_scope_ids_cover_the_top_25_gap_exactly
- tests/unit/strata/test_litmus_cwe.py::TestFiringFromParsedSurfaceSource::test_fires_undischarged[CWE-502]
- tests/unit/strata/test_litmus_cwe.py::TestFiringFromParsedSurfaceSource::test_fires_undischarged[CWE-78]
- tests/unit/strata/test_litmus_cwe.py::TestFiringFromParsedSurfaceSource::test_fires_undischarged[CWE-79]
- tests/unit/strata/test_litmus_cwe.py::TestFiringFromParsedSurfaceSource::test_fires_undischarged[CWE-89]
- tests/unit/strata/test_litmus_cwe.py::TestFiringFromParsedSurfaceSource::test_fires_undischarged[CWE-918]
- tests/unit/strata/test_litmus_cwe.py::TestFiringFromParsedSurfaceSource::test_fires_undischarged[CWE-922]
- tests/unit/strata/test_litmus_cwe.py::TestFiringFromParsedSurfaceSource::test_fires_undischarged[CWE-94]
- tests/unit/strata/test_litmus_cwe.py::TestHardenedDischargesFromParsedSurfaceSource::test_discharges_cleanly[CWE-502]
- tests/unit/strata/test_litmus_cwe.py::TestHardenedDischargesFromParsedSurfaceSource::test_discharges_cleanly[CWE-78]
- tests/unit/strata/test_litmus_cwe.py::TestHardenedDischargesFromParsedSurfaceSource::test_discharges_cleanly[CWE-79]
- tests/unit/strata/test_litmus_cwe.py::TestHardenedDischargesFromParsedSurfaceSource::test_discharges_cleanly[CWE-89]
- tests/unit/strata/test_litmus_cwe.py::TestHardenedDischargesFromParsedSurfaceSource::test_discharges_cleanly[CWE-918]
- tests/unit/strata/test_litmus_cwe.py::TestHardenedDischargesFromParsedSurfaceSource::test_discharges_cleanly[CWE-922]
- tests/unit/strata/test_litmus_cwe.py::TestHardenedDischargesFromParsedSurfaceSource::test_discharges_cleanly[CWE-94]
- tests/unit/strata/test_litmus_cwe.py::TestSharedExecCapabilityDischargesIndependently::test_vuln_fixture_fires_both_independently
- tests/unit/strata/test_litmus_cwe.py::TestSharedExecCapabilityDischargesIndependently::test_hardened_fixture_discharges_both_independently
- tests/unit/strata/test_litmus_cwe.py::TestSharedExecCapabilityDischargesIndependently::test_discharging_only_one_leaves_the_other_undischarged
- tests/unit/strata/test_litmus_cwe.py::TestCapabilityKindNoneEntriesNeverFireByDesign::test_never_fires_even_in_a_plausible_vulnerable_scenario[CWE-22]
- tests/unit/strata/test_litmus_cwe.py::TestCapabilityKindNoneEntriesNeverFireByDesign::test_never_fires_even_in_a_plausible_vulnerable_scenario[CWE-352]
- tests/unit/strata/test_litmus_cwe.py::TestCapabilityKindNoneEntriesNeverFireByDesign::test_never_fires_even_in_a_plausible_vulnerable_scenario[CWE-798]
- tests/unit/strata/test_litmus_cwe.py::TestCapabilityKindNoneEntriesNeverFireByDesign::test_capability_kind_is_none_for_all_three
attachments: []
acceptance: []
threat: null
```
Every WeaknessEntry in CWE_CATALOG and CWE_TOP_25_CATALOG must be exercised by a real .strata litmus project in which its obligation FIRES from parsed surface source (strata_core parse of a .strata file), not from hand-built kernel objects -- plus a hardened variant that discharges it wherever the kernel can express the mitigation. Parametrize the test over the union of both catalogs so adding a WeaknessEntry without a firing fixture FAILS the suite (vacuous-pass doctrine, drift-lock style like the tmLanguage keyword parity test). Follow the existing vuln/hardened litmus pair precedent. OutOfScopeEntry rows are exempt but the test must assert the exemption list matches the catalog's out-of-scope ids exactly so nothing silently escapes.

## Done report

Changed:
- tests/unit/strata/litmus/cwe_79_vuln.strata, cwe_79_hardened.strata (CWE-79, may "html_render")
- tests/unit/strata/litmus/cwe_89_vuln.strata, cwe_89_hardened.strata (CWE-89, may "sql")
- tests/unit/strata/litmus/cwe_exec_vuln.strata, cwe_exec_hardened.strata (CWE-78 + CWE-94 shared, may "exec")
- tests/unit/strata/litmus/cwe_918_vuln.strata, cwe_918_hardened.strata (CWE-918, may "fetch_url")
- tests/unit/strata/litmus/cwe_502_vuln.strata, cwe_502_hardened.strata (CWE-502, may "deserialize")
- tests/unit/strata/litmus/cwe_922_vuln.strata, cwe_922_hardened.strata (CWE-922, may "client_storage")
- tests/unit/strata/litmus/cwe_22_unfired.strata, cwe_352_unfired.strata, cwe_798_unfired.strata (design-finding: capability_kind=None, never fire under THREAT003 -- asserted explicitly, not skipped)
- tests/unit/strata/test_litmus_cwe.py (new, 27 tests: fixture-coverage drift-lock, out-of-scope exemption exactness, parametrized firing/discharge over the union catalog, shared-exec independence, capability_kind=None non-firing)
- docs/strata/threat.md#litmus-coverage (new section: fixture-pair convention, the shared-exec join, the three-id design finding, the out-of-scope boundary proof)

Evidence: 27 node ids recorded via `frob ticket evidence T-0145 <ids>` (tests/unit/strata/test_litmus_cwe.py, all classes) -- `uv run pytest tests/unit/strata/test_litmus_cwe.py -q` -> 27 passed. Full `tests/unit/strata/` suite (528 tests) also passes unchanged.

Filed: T-0149 (frob test: no [[test.runner]] for language=strata blocks touched-set selection on .strata fixtures -- `frob test --base main` errors NoRunner when new .strata files are touched; out of T-0145's declared scope, frob.toml is not in scope). No other out-of-scope findings.

Gates: `frob check --ticket T-0145` clean -- Tool summary all `pass` (ruff-check, ruff-format, ty, frob-cycle, frob-dup, frob-arch, frob-exports x17), gates line `pass  gates  87 violation(s), 57 waived` (main baseline: 87 violations / 55 waived; the +2 waivers are `frob:waive PERF003 reason="two set comprehensions over small fixtures, not a join"` on two new test methods in test_litmus_cwe.py, matching the identical waiver already used four times in test_threat.py for the same false-positive shape -- violation COUNT unchanged from baseline, no new unwaived violations). `frob test --base main` currently errors before running (NoRunner for language=strata, T-0149) -- a pre-existing tooling gap this ticket's fixtures exposed, not a regression from this diff; verified correctness instead via direct `uv run pytest`.

<!-- ticket:T-0146 -->
```yaml
id: T-0146
title: 'cvelistV5 record parser: pydantic models for CVE Record Format v5'
state: done
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/cve/**
- tests/unit/cve/**
- docs/modules/cve.md
- docs/index.md
- tickets.md
evidence:
- tests/unit/cve/test_parser.py::test_parse_log4shell_multi_adp_and_cwe
- tests/unit/cve/test_parser.py::test_parse_version_ranges_with_less_than
- tests/unit/cve/test_parser.py::test_parse_multi_vendor_affected
- tests/unit/cve/test_parser.py::test_parse_cvss_v4
- tests/unit/cve/test_parser.py::test_parse_rejected_record
- tests/unit/cve/test_parser.py::test_parse_missing_file
- tests/unit/cve/test_parser.py::test_parse_truncated_json
- tests/unit/cve/test_parser.py::test_parse_missing_required_field
- tests/unit/cve/test_parser.py::test_iter_mirror_yields_records_and_errors
- tests/unit/cve/test_parser.py::test_iter_mirror_invalid_root
- tests/unit/cve/test_parser.py::test_cve_module_end_to_end_over_mirror
- tests/unit/cve/test_parser.py::test_fixtures_are_ascii_and_escaped_unicode_round_trips
attachments: []
acceptance: []
threat: null
```
Parser for CVE Record Format v5 JSON as published in github.com/CVEProject/cvelistV5. Pydantic v2 models: cveMetadata (id/state/dates), containers.cna and containers.adp (affected products with vendor/product/versions incl. lessThan/lessThanOrEqual/versionType/status semantics, problemTypes with CWE ids, metrics CVSS v3.1 and v4.0, references, descriptions), REJECTED-state records. parse_record(path) and iter_mirror(dir) over a local clone/snapshot layout (cves/YYYY/NNNxxx/CVE-*.json). typani Result error values; an unparseable record is a loud typed failure, never a silent skip (vacuous-pass doctrine). NO network anywhere: tests run against a handful of real record JSONs committed as fixtures covering the shape variety (version ranges, multiple containers, rejected, cwe-bearing problemTypes). This ticket is parser+models only; vet integration is the follow-up ticket.

## Done report

Changed:
- src/frob/cve/_models.py (new) -- CveState, CveError, CveMetadata, Version, Affected, ProblemTypeDescription, ProblemType, Cvss, Metric, Reference, Description, CnaContainer, AdpContainer, CveContainers, CveRecord
- src/frob/cve/_parser.py (new) -- parse_record, iter_mirror
- src/frob/cve/__init__.py (new) -- public exports
- tests/unit/cve/__init__.py (new)
- tests/unit/cve/test_parser.py (new) -- 11 tests
- tests/unit/cve/fixtures/*.json (new, 5 files) + tests/unit/cve/fixtures/mirror/... (new, 7 files: the same 5 records laid out under cves/YYYY/NNNxxx/, plus a truncated-JSON file and a structurally-invalid record for the error-path tests)
- docs/modules/cve.md (new)
- docs/index.md (linked docs/modules/cve.md)

Fixtures are REAL CVE Record Format v5 JSON, fetched directly from raw.githubusercontent.com/CVEProject/cvelistV5/main (network used only during authoring/fixture-collection, never in the parser or in any test):
- CVE-2021-44228 (Log4Shell): 2 ADP containers, CVSS v3.1 on an ADP container (baseScore=10, CRITICAL), CNA problemTypes with 3 real CWE ids (CWE-502, CWE-400, CWE-20).
- CVE-2023-38545 (curl SOCKS5 heap overflow): affected[].versions[] with lessThan + versionType="semver", both "affected" and "unaffected" statuses in one list.
- CVE-2024-3094 (xz backdoor): multiple affected[] entries across vendors (xz upstream + several Red Hat products), defaultStatus="unaffected" alongside explicit versions.
- CVE-2024-4681: CNA metrics carrying a real cvssV4_0 score (found via `gh api search/code -f q='cvssV4_0 repo:CVEProject/cvelistV5'`).
- CVE-2024-7039: REJECTED-state record (found via `gh api search/code -f q='"state": "REJECTED" repo:CVEProject/cvelistV5'`) -- parses fully into CveState.REJECTED with dateRejected populated; cna container is near-empty (only rejectedReasons, which this module does not model and correctly ignores as an extra field).

Every model uses `model_config = ConfigDict(frozen=True, extra="ignore")` (repo convention per src/frob/vet/_models.py): unknown fields never fail parsing, but a missing required field (cveMetadata.state, containers.cna, affected[].versions[].version/status) raises pydantic ValidationError, caught and turned into `Err(CveError.MalformedRecord)` -- verified directly by test_parse_missing_required_field against a hand-built fixture missing cveMetadata.state.

Evidence: 11 pytest node ids (10 unit + 1 integration satisfying TEST003 on src/frob/cve), bound via `frob ticket evidence T-0146`:
- tests/unit/cve/test_parser.py::test_parse_log4shell_multi_adp_and_cwe
- tests/unit/cve/test_parser.py::test_parse_version_ranges_with_less_than
- tests/unit/cve/test_parser.py::test_parse_multi_vendor_affected
- tests/unit/cve/test_parser.py::test_parse_cvss_v4
- tests/unit/cve/test_parser.py::test_parse_rejected_record
- tests/unit/cve/test_parser.py::test_parse_missing_file
- tests/unit/cve/test_parser.py::test_parse_truncated_json
- tests/unit/cve/test_parser.py::test_parse_missing_required_field
- tests/unit/cve/test_parser.py::test_iter_mirror_yields_records_and_errors
- tests/unit/cve/test_parser.py::test_iter_mirror_invalid_root
- tests/unit/cve/test_parser.py::test_cve_module_end_to_end_over_mirror (kind="integration", satisfies TEST003 for src/frob/cve)

Full suite: `uv run pytest -q` -- all pass (2 pre-existing skips, unrelated to this change).
Touched-set: `frob test --base main` -- python runner exit=0.

Waivers (4, all PERF003, all in tests/unit/cve/test_parser.py, all the same shape -- a flat set/list/dict comprehension or a short `for container in (cna, *adp): for x in container.y` walk over 1-7 small fixture records, none inherently a join): lines 14, 47, 133, 173. Each carries its own `frob:waive PERF003 reason="..."` directive at point of use.

Gates: `frob check --ticket T-0146` clean -- pass, 87 violation(s), 59 waived (matches the 87-violation main baseline exactly; the +4 waived count is this ticket's 4 new waivers, no new unwaived violations attributable to this diff). Verified by diffing `frob check` (no ticket) against main before/after: both report 87 violation(s).

Filed: none (no out-of-scope work discovered).

Not closed and not committed per process instructions -- ticket left in-progress for review.

### Post-REJECT addendum

Reviewer REJECTed on two findings; everything else (schema fidelity, error paths, no-network, Result convention, waivers, tests, docs) was verified clean and left untouched.

**1. MAJOR -- non-ASCII bytes in fixtures (fixed).** `CVE-2021-44228.json` had a literal U+2019 curly apostrophe (2 occurrences, "Microsoft's Response..." reference name) and `CVE-2024-4681.json` had literal German umlauts in its `de`-language description. Both files (top-level fixture and the copy under `fixtures/mirror/...`) were re-serialized with `json.dump(obj, fh, ensure_ascii=True, indent=4)` after `json.load`-ing the original bytes -- this re-encodes every non-ASCII character as a `\uXXXX` escape without touching JSON structure or field order, so the records stay byte-for-byte semantically identical (verified: `parse_record` on the re-serialized `CVE-2024-4681.json` still returns the German description starting with "Es wurde eine Schwachstelle...", and the escaped apostrophe in the Log4Shell reference decodes back to the original curly-quote character). All 4 affected files (`CVE-2021-44228.json`, `CVE-2024-4681.json`, and their `fixtures/mirror/cves/.../` copies) now contain zero bytes >= 0x80, confirmed via `grep -P '[^\x00-\x7F]'` returning empty across the whole `tests/unit/cve/fixtures/` tree.

Added `test_fixtures_are_ascii_and_escaped_unicode_round_trips` to `tests/unit/cve/test_parser.py`: asserts every file under `tests/unit/cve/fixtures/` (via `rglob("*.json")`) is pure ASCII bytes, and that `CVE-2024-4681.json`'s German description round-trips through `parse_record` to the expected unicode string (checked via `chr(0xFC)` rather than a literal umlaut in the test source, so the test file itself stays ASCII per the same repo-wide rule -- writing the literal character directly was blocked by this environment's own ASCII-enforcement hook, which is a live demonstration that the rule is real and load-bearing, not just documentation). This locks both directions: no future fixture add can reintroduce raw non-ASCII bytes, and the escaping cannot silently corrupt the represented text.

**2. MINOR -- curl fixture (CVE-2023-38545.json) authenticity (verified, no change).** Re-fetched the live upstream record from `raw.githubusercontent.com/CVEProject/cvelistV5/main/cves/2023/38xxx/CVE-2023-38545.json` and diffed it against the committed fixture with `diff <(python3 -m json.tool fixture) <(python3 -m json.tool upstream)` -- empty diff, i.e. byte-for-byte identical after whitespace normalization. The back-to-back Siemens `affected[]` entries (RUGGEDCOM APE1808, two near-duplicate SIMATIC S7-1500 CPU 1518-4 PN/DP MFP entries, SIMATIC S7-1500 CPU 1518F-4 PN/DP MFP, SIPLUS S7-1500 CPU 1518-4 PN/DP MFP) and the `version == lessThan == "8.4.0"` / `"7.69.0"` range shapes are genuinely present in Siemens ProductCERT's real ADP submission upstream, not a fetch or transcription artifact -- ADP data from third-party coordinators is exactly this messy in practice (repeated product entries at slightly different granularity, ranges expressed as a single boundary point). Kept verbatim; no fixture change was needed or made for this finding.

**Re-measured numbers after both fixes:**
- `uv run pytest tests/unit/cve -q`: 12 passed (was 11; +1 new hygiene test).
- `uv run pytest -q` (full suite): all pass, 2 pre-existing skips, unrelated.
- `frob test --base main`: python runner exit=0.
- `frob check --ticket T-0146`: pass, 87 violation(s), 60 waived (was 59; the new hygiene test's `next(d.value for d in ... if d.lang == "de")` lookup tripped one new PERF003, waived in place with its own `frob:waive` directive -- same shape as the pre-existing waivers, a single filtered lookup over one record's short list, not a nested join).
- Evidence: 12 pytest node ids now bound (added `tests/unit/cve/test_parser.py::test_fixtures_are_ascii_and_escaped_unicode_round_trips` via `frob ticket evidence T-0146`).

Still not closed, still not committed.

<!-- ticket:T-0147 -->
```yaml
id: T-0147
title: 'frob vet: match dependencies against a local cvelistV5 mirror, link CVEs to
  the threat catalog'
state: done
kind: feature
origin: human
created: '2026-07-18'
blocked_by:
- T-0146
parent: null
scope:
- src/frob/cve/**
- src/frob/vet/**
- tests/unit/cve/**
- docs/modules/vet.md
- tickets.md
- src/frob/app/config.py
- src/frob/app/vet_runner.py
- src/frob/__main__.py
evidence:
- tests/unit/cve/test_vet_match.py::test_affected_within_clean_semver_range
- tests/unit/cve/test_vet_match.py::test_unaffected_via_less_than_boundary
- tests/unit/cve/test_vet_match.py::test_unaffected_via_default_status
- tests/unit/cve/test_vet_match.py::test_indeterminate_versiontype_custom_never_silently_unaffected
- tests/unit/cve/test_vet_match.py::test_indeterminate_default_status_unknown
- tests/unit/cve/test_vet_match.py::test_rejected_record_skipped_never_matched
- tests/unit/cve/test_vet_match.py::test_cwe_linkage_catalog_out_of_scope_and_unmapped
- tests/unit/cve/test_vet_match.py::test_log4shell_end_to_end_cwe_linkage_via_mirror
- tests/unit/cve/test_vet_match.py::test_missing_mirror_is_loud_typed_failure
- tests/unit/cve/test_vet_match.py::test_no_dependencies_still_walks_mirror_cleanly
- tests/unit/cve/test_vet_match.py::test_unconfigured_mirror_is_a_silent_no_op
attachments: []
acceptance: []
threat: null
```
Build on the T-0146 parser: frob vet gains CVE matching against a local cvelistV5 mirror directory (configured via [tool.frob] in pyproject.toml; explicit CLI flag override). Match project dependencies (name plus installed version) against affected[] product/version ranges honoring lessThan/lessThanOrEqual/versionType/status semantics; report CVE id, CVSS score/severity, and description. Link each CVE's problemTypes CWE ids to the strata threat catalog (CWE_CATALOG plus CWE_TOP_25_CATALOG) so a dependency CVE citing e.g. CWE-89 names the catalog entry and mitigation that covers it, and OutOfScopeEntry ids are reported as such. Loud typed failure when a mirror path is configured but missing or unreadable (vacuous-pass doctrine); clean no-op only when no mirror is configured. Tests: fixture mirror dir with a handful of real records; matching cases covering range semantics, rejected records skipped-with-log, and the CWE linkage.

Scope note (added during implementation): the ticket's own "explicit CLI flag override" requirement for the mirror path is unsatisfiable without touching CLI wiring, which lives outside src/frob/vet/**/src/frob/cve/** -- src/frob/app/config.py (AppConfig.vet_cve_mirror field, [tool.frob] wiring), src/frob/app/vet_runner.py (--cve-mirror dispatch, output), and src/frob/__main__.py (the --cve-mirror argparse flag) were added to scope for this reason. No other files outside the original scope were touched.

## Done report

Changed:
- src/frob/vet/_cve.py (new): MatchStatus, CweDisposition, CweLink, CveMatch, link_cwe_ids, match_dependencies_against_mirror, plus private helpers (_evaluate_entry, _status_for_affected, _product_matches, _best_cvss, _description_summary, _cwe_ids_of, _match_record_dependency, _cwe_catalog_index, _cwe_out_of_scope_index, _parse_comparable)
- src/frob/vet/_models.py::VetError (added CveMirrorInvalid member)
- src/frob/vet/__init__.py (re-exports new _cve.py symbols)
- src/frob/app/config.py::AppConfig (added vet_cve_mirror field, wired into from_external's path-field loop) [scope extension, justified above]
- src/frob/app/vet_runner.py::_cve_matches_for, _print_cve_table, _run_scan (CLI dispatch + table/JSON output) [scope extension]
- src/frob/__main__.py::_add_vet_parser (--cve-mirror flag) [scope extension]
- docs/modules/vet.md (new "CVE mirror matching (T-0147)" section, public-api anchors, Implementation notes)
- tests/unit/cve/test_vet_match.py (new, 11 tests)
- tests/unit/cve/fixtures/vet_mirror/cves/2024/1xxx/CVE-2024-1000.json, CVE-2024-1001.json (new synthetic fixtures; see docs/modules/vet.md Implementation notes for why a separate mirror from the T-0146 real-record one was needed)
- tickets.md (this ticket's scope list + Done report)

Evidence: 11 pytest node ids under tests/unit/cve/test_vet_match.py, recorded via `frob ticket evidence T-0147` (see this ticket's evidence: list above). Measured: `pytest tests/unit/cve/ tests/test_vet.py tests/test_vet_containment.py -q` -> 121 collected, 0 failures (121 = 76 + 22 + 12 + 11 across the four files, verified via --collect-only -q; the -q run itself shows dot-progress only, no summary line, under this repo's pytest-xdist config). `frob test --base main` selected touched-set python suite -> exit=0, 2.18s. `ruff check`/`ruff format --check`/`ty check` on every touched file -> clean. Manual CLI verification: `frob vet <dir> --cve-mirror <mirror>` (table and --json output) and the unconfigured/no-op and missing-mirror-loud-failure paths, all exercised by hand against a throwaway uv.lock fixture in /tmp, matching the automated test coverage.

Filed: none (no out-of-scope work discovered beyond the three CLI-wiring files already declared above).

Gates: `frob check --ticket T-0147` -- gates stage reports "pass, 87 violation(s), 67 waived" (0 unwaived violations attributable to this ticket's scope after: (1) 3 PERF001/PERF003 false-positive waivers added in this diff with specific reasons -- see src/frob/vet/_cve.py, src/frob/app/vet_runner.py, tests/unit/cve/test_vet_match.py; (2) SCOPE001/PRE001 cleared by extending T-0147's scope + `frob ticket sweep T-0147` per the justification above). The single remaining FAIL line (`ruff-format: 1 file would be reformatted`, tests/unit/cve/test_parser.py) is pre-existing on main -- verified independently by running `ruff format --check` against the main-branch copy of that file, which also fails; not touched by this diff, left for T-0148 (drive frob check gates to zero).

Known cuts (disclosed, not silently dropped): no VET-numbered gate rule feeds CVE matches into `frob check`'s enforce/exit-code path yet (reporting-only this slice, `VET012`-shaped follow-up candidate); product matching is exact case-insensitive string match against `affected[].product`, not a real CPE-dictionary join (undercounts, documented in docs/modules/vet.md).

<!-- ticket:T-0148 -->
```yaml
id: T-0148
title: drive frob check gates to zero violations
state: queued
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/**
- tests/**
- docs/**
- frob.toml
- pyproject.toml
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
The gates stage currently reports 87 violation(s), 55 waived on main. End state: the gates line reports 0 violation(s). Triage every reported item: (1) fix it properly, (2) add a narrowly-scoped frob:waive with a specific written reason where the rule genuinely misfires, or (3) file a specific follow-up ticket and mark the site frob:todo T-#### when the fix is real but out of scope. No blanket or file-level waivers; no rule disabling in frob.toml without a written rationale in the Done report. Document the per-rule-family outcome table (family, count, disposition) in the Done report. Run AFTER the current wave lands (T-0140/T-0141/T-0144/T-0145/T-0146 touch overlapping files).

<!-- ticket:T-0149 -->
```yaml
id: T-0149
title: 'frob test: no [[test.runner]] for language=strata blocks touched-set selection
  on .strata fixtures'
state: done
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- frob.toml
- tickets.md
evidence:
- tests/test_testing.py::TestRunners::test_placeholder_files
- tests/test_testing.py::TestRunners::test_no_runner_error
- tests/test_testing.py::TestRunners::test_valid_runner_loaded
attachments: []
acceptance: []
threat: null
```
Found while working T-0145: adding new .strata files under tests/unit/strata/litmus/ (or anywhere) makes frob test --base main fail with NoRunner: 'language strata has selected tests but no runner -- add a [[test.runner]] entry'. frob.toml has runners for python and rust only; strata surface files (.strata) are a distinct language frob.lang/frob.testing classifies but there is no [[test.runner]] entry (and likely no sensible native pytest-equivalent for a .strata file standalone -- it is exercised THROUGH the python tests that parse it, e.g. test_litmus_cwe.py). Needs either: (1) a [[test.runner]] entry that maps .strata files to the python test files that bind them (frob:tests directives already exist on the fixtures' consuming test modules), or (2) frob.testing/select_tests excluding .strata from touched-set language classification entirely since it is data, not directly-runnable source. Verified reproducing: touching tests/unit/strata/litmus/*.strata and running 'frob test --base main' errors NoRunner before running any tests.

## Done report

Changed:
- frob.toml: fourth [[test.runner]] entry, language = "strata" -- command
  runs `uv run pytest -q tests/unit/strata {files}` (touched .strata paths
  fold in beside the covering suite dir, contributing zero collected
  items), all_command runs the suite dir. Deliberately narrower than a
  global fallback = "suite".

Evidence: config-only change with no code symbol of its own; the three
attached node ids (TestRunners::test_placeholder_files / test_no_runner_error /
test_valid_runner_loaded) evidence the exact machinery this entry relies
on -- {files} expansion, the NoRunner failure mode being fixed, and
runner-spec loading. The behavior change itself was verified by direct
reproduction, independently re-executed by the reviewer:
- pre-fix: `frob test --base ea4d24f` errors NoRunner for language
  'strata'; post-fix: [PASS] strata exit=0, [PASS] python exit=0.
- the exact constructed command run by hand (pytest with a .strata path
  argument) exits 0 with 528 items collected -- {files} expansion is
  harmless for non-python paths per _expand_placeholder semantics.
- no-strata touched-sets unchanged (nothing-touched selects no tests).

Gates: `frob check --ticket T-0149` pass, 87 violation(s)/57 waived,
identical to the post-T-0145 main baseline; reproduced twice by the
reviewer. Reviewer verdict: APPROVE.

Filed: none.

<!-- ticket:T-0150 -->
```yaml
id: T-0150
title: 'self-conformance: vet capability scan of our own source must match design/frob.strata
  interfaces'
state: done
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- src/frob/app/sys_runner.py
- src/frob/app/config.py
- src/frob/app/__main__.py
- design/frob.strata
- tests/unit/strata/**
- docs/strata/**
- frob.toml
- tickets.md
- tests/golden/frob_export_seccomp.json
- tests/system/test_frob_self_model.py
evidence:
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceCore::test_core_undeclared_interface_fires
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceCore::test_core_undeclared_interface_discharges_once_declared
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceExtended::test_extended_undeclared_interface_fires
- tests/unit/strata/test_selfconform.py::TestUndeclaredInterfaceExtended::test_extended_undeclared_interface_discharges_once_declared
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_stale_design_fires
- tests/unit/strata/test_selfconform.py::TestStaleDesign::test_stale_design_discharges_once_observed
- tests/unit/strata/test_selfconform.py::TestUnmodeledCode::test_unmodeled_code_fires
- tests/unit/strata/test_selfconform.py::TestUnmodeledCode::test_unmodeled_code_discharges_once_mapped
- tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_parses_and_elaborates
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_every_claim_proves
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
attachments: []
acceptance: []
threat: null
```
frob vet already introspects dependencies for capability use (scan_directory_capabilities in src/frob/vet/_capability.py: exec/eval/network/fs/... per-language token scan). Point that same machinery at OUR OWN src/ tree and reconcile against the self-hosted strata design, so the interfaces recorded in design/frob.strata are provably in sync with what the code actually does. Reuse scan_directory_capabilities READ-ONLY (import it; do not modify src/frob/vet -- T-0147 is concurrently editing that package). Mechanism: a node-to-source-path mapping (investigate whether the kernel/surface already supports binding a node to a code path; if not, add the smallest principled mapping -- e.g. a [tool.frob]/frob.toml table or a strata clause -- and document the decision). Conformance rules, all loud (vacuous-pass doctrine): (1) capability observed in a mapped path but not declared on the mapped node = violation (undeclared interface); (2) capability declared on a node with zero observed sites in its mapped paths = violation (stale design); (3) source directories under src/ with no node mapping = violation (unmodeled code), no silent exemption; test paths excluded per _is_test_path precedent. Surface as a new SYS-family gate rule id wired into frob sys audit (follow the THREAT/SYS rule registration precedent) and run against design/frob.strata in our own gates. Expect the first honest run to FAIL until design/frob.strata is updated to declare reality -- updating the design to match observed capabilities (or waiving with written reasons) is part of this ticket. Tests: fixture design+source trees for each rule firing and discharging; drift-lock so an unmapped capability kind in the scanner vocabulary fails loudly rather than being silently ignored.

## Done report

### POST-REJECT ADDENDUM (rework round)

The reviewer's CRITICAL finding was correct: T-0132 landed the `code STRING+`/
`may STRING` surface grammar (`strata-core/src/parse.rs::parse_node`) well
before this ticket's merge-base, so `design/frob.strata`'s own header claim
("`code=`/`may` not reachable from `.strata` source text") was ALREADY
STALE when I read and trusted it. The entire first-round mechanism (a
parallel `[strata.code_map]`/`[strata.capability_map]` `frob.toml` table
pair) was built on that false premise and has been deleted in full:
`frob.toml` and `src/frob/strata/_errors.py` are now byte-identical to
`main` (`git diff frob.toml src/frob/strata/_errors.py` is empty).

Reworked mechanism -- `code "glob";`/`may "kind";` declared DIRECTLY on
`design/frob.strata`'s nodes, reusing `bind_code` (T-0078) verbatim and
delegating SYS100's net/fs-write/exec slice to `check_capability_
conformance`/THREAT004 (T-0079/T-0113) verbatim -- zero new detection for
that slice. Only SYS100's eval/env/ffi/install-hook slice, all of SYS101,
and all of SYS102 are new code, each with a written gap statement in
`_selfconform.py`'s module docstring and `docs/strata/selfconform.md`
explaining precisely why the existing machinery cannot express it. Also
fixed `design/frob.strata`'s stale header comment itself (the doc-drift
the reviewer flagged as in-scope).

One real, narrow grammar gap surfaced during the rework and is NOT fixed
here (filed separately, see Filed below): `store` declarations
(`parse_store`) do not actually accept `code`/`may`, despite `docs/
strata/surface.md`'s `store_prop := node_prop | ...` line claiming
otherwise. `tickets_ledger` (a `store`) declares neither; the code that
writes to it (`src/frob/tickets/**`) is folded into `core`'s `code`/`may`
instead, consistent with `core`'s existing `f_core_tickets` flow.

Changed (this round, full list):
- src/frob/strata/_selfconform.py (new, REWRITTEN from round 1): check_self_conformance, SYS_UNDECLARED_INTERFACE/SYS_STALE_DESIGN/SYS_UNMODELED_CODE, SelfConformReport/SelfConformViolation, _core_undeclared_violations (delegates to THREAT004), _extended_kind_violations, _stale_design_violations, _unmodeled_violations, _EXTENDED_KINDS -- no frob.toml reads anywhere
- src/frob/strata/__init__.py -- exports updated for the above (SYS_* names unchanged, function set changed)
- src/frob/strata/_errors.py -- REVERTED to main (UnknownCapabilityKind/MalformedSelfConformMap deleted, no longer needed)
- frob.toml -- REVERTED to main (no [strata.*] tables)
- src/frob/app/sys_runner.py -- unchanged from round 1 (_run_audit calls check_self_conformance; the call site didn't need to change, only what it calls into)
- design/frob.strata -- header comment corrected (T-0132 grammar exists); every real `node` (cli/graphlang/gates/checker/stratamod/core/vet) gets `code "..."` + `may "..."` from a real `scan_file_capabilities` sweep; `tickets_ledger` (store) gets neither (grammar gap above), its code folded into `core`; 3 new `assume "weakness:CWE-78:<node>"` discharge claims (checker/core/vet) since declaring real `may "exec"` drags in a THREAT003 obligation `_effects.py`'s `may`-analog never existed to discharge before
- src/frob/strata/_threat.py -- new `DEFAULT_BENIGN_CAPABILITIES` (7 entries: exec + the 6 tier-2/vet kinds with no CWE_CATALOG analog), each with a written reason; `exec` is listed despite having a real catalog entry because `QUALITY_CATALOG` (unlike `CWE_CATALOG`) has none, and `_evaluate_family` shares one `benign` tuple across both loops
- src/frob/strata/_audit.py -- `evaluate_exhaustiveness` gets a `benign` parameter defaulting to `DEFAULT_BENIGN_CAPABILITIES` (previously hardcoded `()`), threaded into both the security and quality `_evaluate_family` calls
- src/frob/strata/_sysdoc.py -- `audit_claim`'s `benign` default likewise changed from `()` to `DEFAULT_BENIGN_CAPABILITIES` (this is the DOC003 code path `frob.gates.sys_gate` actually calls -- discovered only by running the real self-model test, not by unit-testing `_audit.py` alone)
- docs/strata/selfconform.md -- REWRITTEN for the reworked mechanism, kind-space drift-lock, and the store/`core`-folding decision
- tests/unit/strata/test_selfconform.py -- REWRITTEN, 10 tests (measured via `pytest --collect-only`, not estimated -- round 1's claimed "17" was wrong, this round's actual count is 10): TestUndeclaredInterfaceCore (2, THREAT004 delegation), TestUndeclaredInterfaceExtended (2, new eval/env/ffi/install-hook code), TestStaleDesign (2), TestUnmodeledCode (2), TestExtendedKindsDriftLock (1), TestRealGateGreen (1)
- tests/golden/frob_export_seccomp.json -- regenerated (byte-for-byte derivative of design/frob.strata's now-populated `may` atoms; k8s/iam goldens unchanged since those exporters don't render `may`) -- SCOPE EXTENSION, written justification: this file is a pure, deterministic function of design/frob.strata (in original scope) computed by an already-shipped exporter; leaving it stale would fail test_export_golden.py::test_seccomp, a pre-existing regression test whose entire job is catching exactly this kind of silent drift
- tests/system/test_frob_self_model.py -- test_parses_and_elaborates' hardcoded claim count (3 -> 6) and test_every_claim_proves' verdict assertions (all-PROVED -> 3 PROVED + 3 ASSUMED, never REFUTED) updated to match the 3 new discharge claims -- SCOPE EXTENSION, same justification: hardcoded counts against design/frob.strata's real structure, in original scope, would otherwise regress from my own in-scope design change

Real measured numbers (2026-07-18, `scan_file_capabilities` over every file `bind_code` binds via each node's real `code=` glob, after the rework):
- cli={eval,fs}, graphlang={eval,fs}, gates={eval,fs}, checker={exec,fs}, stratamod={eval,ffi,net} (NOT fs -- round 1's "fs" on stratamod was itself an artifact of round 1's own since-deleted frob.toml reader's `.open("rb")` call; re-measured honestly after the rework removed that code, and it is gone), vet={env,eval,exec,ffi,fs,install-hook,net}, core={env,eval,exec,fs} (tickets/** folded in, same set)
- `check_self_conformance(model, root)` against the real repo: 0 violations (SYS100=0, SYS101=0, SYS102=0), verified via `uv run python -c "..."` direct call and `TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant`
- `uv run frob sys audit`: exit 0, "self-conformance PROVED -- zero SYS gaps" alongside THREAT/COMPLIANCE (also PROVED)
- IMPORTANT tooling finding: the bare `frob` command on PATH (`~/.local/bin/frob`) is a STALE globally-installed uv-tool copy that does NOT see edits to this worktree's `src/frob/` -- since T-0150 modifies frob's OWN detection code, every verification command in this ticket must be run as `uv run frob ...`, not bare `frob ...`, or it silently checks old logic. Confirmed by `python3 -c "import frob; print(frob.__file__)"` (global site-packages) vs `uv run python -c "..."` (this worktree's src/frob). This is itself worth flagging for anyone else self-hosting: filed as a note here rather than a separate ticket since it's a workflow finding, not a code bug.

Filed:
- T-0151 (bug, scope src/frob/vet/_capability.py): vet's own capability scanner self-matches its own pattern-table string literals when scanning `_capability.py` itself (e.g. "subprocess.", "compile(", "cmdclass" as DATA, not calls) -- this is what inflated vet's originally-measured eval/exec/ffi/install-hook set almost entirely from one self-referential file; confirmed no real `subprocess`/`os.system`/etc. CALL exists anywhere else in `src/frob/vet/*.py` (direct grep). `vet`'s `may "exec"` discharge claim in design/frob.strata documents this finding inline. A second, narrower instance of the SAME false-positive hit T-0150's OWN new prose (the `DEFAULT_BENIGN_CAPABILITIES` reason strings in `_threat.py` originally said "os.environ/os.getenv" and "cmdclass", both literal needle matches) -- caught by `TestRealGateGreen` failing during this rework and fixed by rewording, not by touching vet.
- The `store_prop` grammar gap (`parse_store` doesn't accept `code`/`may` despite `docs/strata/surface.md` claiming it does) is noted in design/frob.strata's `tickets_ledger` comment and here, but NOT filed as a separate ticket yet -- flagging for the coordinator to file, since T-0150's scope explicitly excludes `strata-core/` and this ticket is already at its complexity budget.

Gates (measured via `uv run frob ...`, the correct local invocation -- see tooling finding above):
- `uv run frob check --ticket T-0150`: exit 0, 94 violations/62 waived, zero non-PERF violations attributable to any file this ticket touches (verified by grepping the unwaived set for every changed filename; only PERF001-004 style suggestions remain, the same pre-existing category every other file in this package already carries)
- `uv run frob sys audit`: exit 0, PROVED across all 8 configured views + self-conformance
- `uv run ruff check` / `ruff format --check` / `ty check`: clean on every changed/new Python file
- `uv run pytest -q tests/unit/strata/ tests/system/test_frob_self_model.py tests/unit/strata/test_export_golden.py`: all pass
- `uv run frob test --base main` (touched-set): exit 0
- Stash-isolated baseline diff (T-0141 precedent) was attempted but the `git stash`-recovered baseline's own `frob check --ticket T-0150` run produced 1106 violations against a `frob.toml`/prework state that does not correspond to any real committed state (T-0150 already existed as a queued ticket at that commit with zero scope work done, which the scope/prework gates treat very differently from "ticket doesn't exist yet") -- not a clean comparison. The exit-0 `uv run frob check --ticket T-0150` result plus the explicit per-file unwaived-violation grep above is the evidence actually relied on for "clean."

Scope note: src/frob/app/config.py and src/frob/app/__main__.py remain in the declared scope but needed no changes in either round.

<!-- ticket:T-0151 -->
```yaml
id: T-0151
title: vet capability scanner self-matches its own pattern-table literals
state: done
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/vet/_capability.py
- tests/test_vet.py
- design/frob.strata
- docs/modules/vet.md
- tickets.md
evidence:
- tests/test_vet.py::TestCapabilityScan::test_re_compile_alone_does_not_report_eval
- tests/test_vet.py::TestCapabilityScan::test_bare_compile_call_still_reports_eval
- tests/test_vet.py::TestCapabilityScan::test_genuine_eval_still_detected
- tests/test_vet.py::TestCapabilityScan::test_capability_module_self_scan_documented_false_positive
- tests/test_vet.py::TestCapabilityScan::test_scan_directory_capabilities_excludes_own_module
attachments: []
acceptance: []
threat: null
```
Found while measuring real capabilities for T-0150's design/frob.strata may declarations: scan_file_capabilities/scan_directory_capabilities substring-matches _PATTERNS' own needle literals (e.g. "subprocess.", "compile(", "cmdclass") when scanning src/frob/vet/_capability.py itself, since those needles are stored as plain string data in that same file. This inflates vet's own observed capability set (T-0150 measured vet as declaring eval/exec/ffi/install-hook/env/net almost entirely from this one file matching itself) and would similarly inflate the scan of any OTHER file that happens to embed one of these substrings in a comment/string/docstring (T-0150's own _threat.py DEFAULT_BENIGN_CAPABILITIES reason strings tripped this exact false-positive during T-0150's rework, before rewording). Needs either: excluding the pattern-table-defining file itself from self-scanning, or a smarter match (e.g. AST-based real call-site detection instead of raw substring match), or a documented/accepted false-positive-rate note in docs/modules/vet.md. Out of scope for T-0150 (scope excludes src/frob/vet -- T-0147 concurrently edits it).

## Done report

Changed:
- src/frob/vet/_capability.py: removed the bare `"compile("` needle from
  the Python `eval` pattern table (it substring-matched `re.compile(`/
  `ast.compile(` everywhere in the repo -- confirmed via direct grep that
  every non-self hit for that needle was a dotted `re.compile(` call, zero
  bare builtin `compile(` calls anywhere in src/frob). Added
  `_has_bare_compile_call` (dot-exclusion text scan, still no AST) wired
  through a new `_SPECIAL_CHECKS` table so `compile(` only counts as
  "eval" when it is NOT a dotted method access. Added `_is_self_path` /
  `_SELF_PATH` so `scan_directory_capabilities` excludes this module's own
  file from directory aggregation (its `_PATTERNS` table is guaranteed to
  contain every needle as literal data). `scan_file_capabilities` called
  directly on this file is unaffected and still exhibits the accepted
  false-positive class, now documented in the module docstring and
  docs/modules/vet.md rather than silently eaten.
- tests/test_vet.py (TestCapabilityScan): 5 new regression tests --
  `re.compile(`/`ast.compile(` alone no longer report "eval"; a genuine
  bare `compile(source, ...)` call still does; genuine `eval(...)` still
  does; scanning `_capability.py` directly still shows the documented
  self-match (locks the accepted-behavior decision either way, per
  ticket instructions); `scan_directory_capabilities` over the real
  `src/frob/vet` path no longer reports "eval"/"exec" (it still reports
  "install-hook" from `_ecosystem.py`'s genuine `"cmdclass" in text`
  check -- a SEPARATE, documented false positive this ticket's cheap
  self-exclusion does not and cannot cheaply fix; asserted explicitly,
  not silently ignored).
- docs/modules/vet.md: new "Self-match false positives (T-0151)"
  paragraph in "Honest limits" documenting the accepted false-positive
  class per the ticket's design constraint (b) -- full AST-based
  precision was explicitly out of scope.

Scope extension (written justification, per ticket instructions):
- design/frob.strata: removed `may "eval";` from the `gates` node. Fixing
  the `compile(` needle changed real observed capabilities -- `frob sys
  audit` immediately fired SYS101 (`eval declared but never observed on
  gates`) after the code fix, since `gates`'s only "eval" evidence was
  always `re.compile(` calls (_FRONTMATTER_RE, _AD_ID_RE, _TODO_RE, etc,
  all regex; confirmed zero real eval/exec/dynamic-import anywhere under
  src/frob/gates/** by direct grep). Leaving the stale `may "eval"` would
  make the ticket's own fix regress self-conformance, which the ticket
  text explicitly puts in scope ("Updating design/frob.strata's may
  declarations ... to the new honest observations is IN SCOPE"). No
  other node's `may "eval"`/`may "exec"` changed: cli (src/frob/app.py's
  `importlib.import_module(`), graphlang (src/frob/lang/_walk_strata.py's
  `importlib.import_module(`), core (src/frob/dup/_pipeline.py's
  `model.eval(`, src/frob/fuzz/_signatures.py's `importlib.import_module(`)
  all still have genuine, non-`compile(` eval-pattern hits -- re-measured
  directly via `scan_directory_capabilities`/grep, not assumed.
- docs/modules/vet.md, tests/test_vet.py, tickets.md: natural homes for
  the documented-limits paragraph, the regression tests, and this Done
  report/evidence/scope record; all three were already implicitly
  expected by the ticket's own text (the ticket names docs/modules/vet.md
  explicitly as the fallback if precision isn't cheaply achievable, and
  ticket evidence/state live in tickets.md by construction).
- tests/golden/frob_export_seccomp.json and
  tests/system/test_frob_self_model.py were NOT touched: both were
  re-run after the design/frob.strata change and neither needed
  regeneration -- `gates`'s exported syscall set is a strict subset of
  what cli/graphlang/core/vet already export for "eval", so dropping one
  node's redundant `may "eval"` did not change the union the exporter
  renders (verified: `git diff --stat` against both files is empty after
  running `uv run pytest -q tests/unit/strata/test_export_golden.py
  tests/system/test_frob_self_model.py`, both green).

Real measured numbers (2026-07-18, `uv run frob sys audit` / direct
`scan_file_capabilities`/`scan_directory_capabilities` calls, this
worktree's `src/frob/`, NOT the stale global `frob` -- see T-0150's
tooling finding, same caveat applies here):
- Before fix: `gates` node's `may "eval"` was satisfied only by
  `re.compile(` hits (12 call sites across src/frob/gates/__init__.py
  and decisions.py/invariants.py); zero genuine eval/exec-adjacent code.
- After fix: `scan_directory_capabilities(src/frob/gates)` no longer
  reports "eval"; `scan_directory_capabilities(src/frob/vet)` no longer
  reports "eval"/"exec" but still reports "install-hook" (documented,
  separate false-positive source, `_ecosystem.py`).
- `uv run frob sys audit`: exit 0, PROVED across all 8 configured views;
  self-conformance PROVED, 0 SYS gaps (confirmed both before-fix failure
  -- 1 SYS101 violation on `gates` -- and after-fix clean state).

Evidence: the 5 node ids attached via `frob ticket evidence T-0151`; all
pass (`uv run pytest -q tests/test_vet.py::TestCapabilityScan`, 12/12).

Filed: none (no out-of-scope work found beyond what was already filed
against T-0151 itself).

Gates (measured via `uv run frob ...`, this worktree's build):
- `uv run frob check --ticket T-0151`: `pass gates 96 violation(s), 67
  waived` -- zero unwaived violations attributable to any file this
  ticket touches (grepped the unwaived set line-by-line for every
  changed filename: the only hit, tests/test_vet.py:598 PERF003, is a
  pre-existing nested-loop warning in `TestEcosystemRules`, several
  hundred lines away from and unrelated to this ticket's additions,
  which start at TestCapabilityScan's new tests appended after line 389;
  every other unwaived violation is TEST002/TEST003/TEST006/PERF00x
  against files this ticket never touched).
- `uv run frob sys audit`: exit 0, PROVED across all 8 configured views
  + self-conformance (0 SYS gaps).
- `uv run ruff check` / `ruff format --check` / `uv run ty check`: clean
  on src/frob/vet/_capability.py and tests/test_vet.py.
- `uv run pytest -q tests/test_vet.py tests/unit/strata/
  tests/system/test_frob_self_model.py`: all pass (no count regression).
- `uv run frob test --base main` (touched-set): exit 0, python suite
  selected and passing.

<!-- ticket:T-0152 -->
```yaml
id: T-0152
title: packaging is an undeclared runtime dependency -- bare frob install crashes
  on import
state: done
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- pyproject.toml
- uv.lock
- tests/unit/test_runtime_deps.py
- tickets.md
evidence:
- tests/unit/test_runtime_deps.py::TestRuntimeDepsDeclared::test_every_unguarded_third_party_import_is_declared
- tests/unit/test_runtime_deps.py::TestRuntimeDepsDeclared::test_packaging_regression_is_locked
attachments: []
acceptance: []
threat: null
```
T-0147's src/frob/vet/_cve.py imports packaging.version at module level, but packaging was only in the dev dependency group -- a bare wheel install (uv tool install / pip install) crashed every frob invocation with ModuleNotFoundError: No module named 'packaging', found when reinstalling the global tool after T-0150 landed. Same defect class as T-0142. Fix: declare packaging>=24 in [project].dependencies; add a drift test asserting every top-level third-party import under src/frob/ resolves to a declared [project] dependency so the next undeclared import fails in CI instead of at install time. Coordinator hotfix: toolchain-blocking, fixed inline with ticket accounting rather than dispatched.

## Done report

Changed:
- pyproject.toml: packaging>=24 added to [project].dependencies with a
  T-0152 comment (was dev-group only; frob.vet._cve imports
  packaging.version at module level, so every bare-wheel invocation
  crashed with ModuleNotFoundError).
- uv.lock: refreshed for the dependency move.
- tests/unit/test_runtime_deps.py (new): drift-lock walking src/frob's
  unguarded top-level imports via AST (module body only, so guarded/lazy
  imports are exempt) and asserting each third-party name maps to a
  declared [project] dependency; plus a pinned regression test for the
  exact packaging/vet._cve incident. Optional extras (z3 via frob[smt])
  and the local native crates are an explicit allow-list.

Evidence: the two node ids attached via frob ticket evidence; both pass.

Verification: reproduced the crash on the freshly reinstalled global
tool (uv tool install via make install-tool -> ModuleNotFoundError:
packaging on every invocation), applied the fix, reinstalled, and the
global frob now runs clean: frob sys audit reports PROVED including
self-conformance, frob --help exits 0.

Process note: coordinator hotfix -- the broken global tool blocked all
ledger operations, so this was fixed inline with ticket accounting
(filed, started, evidenced, closed in order) rather than dispatched to
an implementer; reviewed by the T-0148 sweep as a backstop.

Filed: none.

<!-- ticket:T-0153 -->
```yaml
id: T-0153
title: 'std.cve fingerprints: pattern catalog for known vulnerable-usage classes'
state: queued
kind: security
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- src/frob/vet/_capability.py
- tests/unit/strata/**
- tests/test_vet.py
- docs/strata/threat.md
- docs/modules/vet.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Extend the standard library beyond CWE entries with CVE FINGERPRINTS: code-level patterns for canonical vulnerable-usage classes, so the scanner can flag the pattern in our own code and in vetted dependency source -- not just match dependency versions against the mirror (T-0146/T-0147 handle that). Model: CveFingerprint entries (id, title, cve cite(s), linked cwe id joining the existing catalogs, language, detection needles following vet _capability's recall-over-precision substring philosophy including the T-0151 dot-exclusion lessons, remediation guidance). Curated starter set of 10-15 canonical classes with REAL citations, e.g.: pickle.loads on untrusted data, yaml.load without SafeLoader, subprocess shell=True with interpolation, requests verify=False, weak-hash password storage, jndi-style lookup injection (Log4Shell class), eval on request data, tarfile extractall path traversal, xml external entities. Each fingerprint drift-locked to the CWE catalog (unknown cwe id fails loudly) and exercised by fire/discharge fixtures in the litmus style. Wire into vet scan output and into the threat catalog views as a separate table following the CWE_TOP_25_VIEWS precedent (do not silently widen default views). Honest limits documented: substring fingerprints have false-positive classes -- document them per T-0151's precedent rather than half-building AST precision.

<!-- ticket:T-0154 -->
```yaml
id: T-0154
title: 'PII declarations: first-class personal-data modeling and flow proofs in strata'
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- strata-core/src/**
- src/frob/strata/**
- design/frob.strata
- tests/unit/strata/**
- docs/strata/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
First-class PII in the design language. INVESTIGATE FIRST: the compliance layer (COPPA/GDPR/HIPAA views), kernel Flow/Boundary/Claim machinery, and the T-0132 code/may attr grammar -- reuse, never parallel-build (T-0150 round-1 lesson). Feature: declare what personal data a node/store/flow carries (e.g. carries "pii.email", categories: identifier, contact, financial, health, biometric, behavioral, credentials) in surface grammar + elaboration + kernel; prover joins: PII crossing a trust boundary without a declared protection (encryption/pseudonymization/consent) is a violation; stores carrying PII require declared retention and erasure paths feeding the GDPR/HIPAA views (join to existing compliance obligations rather than duplicating them); undeclared-PII linting where flows source from stores with declared PII. Litmus vuln/hardened pair firing and discharging each new rule from parsed surface source. Self-model: declare frob's own PII posture in design/frob.strata (expected: none beyond git author metadata -- proving the zero case counts and must be explicit, not silent). Seccomp/self-model goldens regenerated if affected, per T-0150 precedent.

<!-- ticket:T-0155 -->
```yaml
id: T-0155
title: 'design lint family: caching, resource bounds, rate-limiting, kill-switch rules
  over the kernel model'
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- design/frob.strata
- tests/unit/strata/**
- docs/strata/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Operational design linting over the kernel model, as a new rule family alongside SYS100-102. INVESTIGATE FIRST: the scenario engine (node loss, rate surge, trust downgrade -- T-0073), Bound/capacity claims, and quantity grammar (rates, sizes) -- reuse their vocabulary. Rules (each loud, waivable only with reason, drift-locked in a rule registry): LINT: public/edge boundary accepting external flows without a declared rate limit; store consumed by flows whose declared rate exceeds the store's declared service rate without a caching/TTL declaration; node participating in a surge scenario without a capacity Bound claim; node holding a risky capability (exec/net per the may declarations from T-0150) without a declared kill-switch/flag mechanism; flow fan-in exceeding declared downstream capacity. Each rule needs a written justification of WHY the kernel can express it (or an honest OutOfScope-style entry if it cannot yet -- follow the threat catalog discipline); fire/discharge litmus fixtures from parsed surface; wired into frob sys audit output beside self-conformance. Apply to design/frob.strata itself and make it green honestly (declare real rate/caching/capacity facts or waive with reasons -- expect cascading consequences per T-0150/T-0151 precedent).

<!-- ticket:T-0156 -->
```yaml
id: T-0156
title: 'release readiness: version, changelog, packaging, and the release gate'
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by:
- T-0148
- T-0153
- T-0154
- T-0155
- T-0157
parent: null
scope:
- pyproject.toml
- CHANGELOG.md
- README.md
- docs/**
- strata-core/Cargo.toml
- frob-core/Cargo.toml
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Get frob into a releasable state once the gates-zero sweep and the three feature tickets land. Deliverables: (1) version bump decision (current 0.1.0 line -- pick the next version honestly against the scale of what shipped) stamped via frob release stamp, with frob release check green as the gate; (2) CHANGELOG.md generated from the ticket archive + git history since the last release, grouped by area (strata, threat/CVE, vet, check/gates, tickets, editors), human-readable, every T-#### referenced; (3) README refresh: current subcommand table, strata overview with the self-model/self-conformance story, editors support, CVE mirror workflow, install paths (uv tool install, bare pip, dev) each verified by actually running them; (4) docs/index.md completeness pass -- every docs/ page linked, every public module documented; (5) packaging: uv build the wheel, decide and document the native-crate strategy (strata-core/frob_core: bundled, separate wheels, or optional with the T-0133-135 degrade contract -- verify the degrade contract works from the actual built wheel in a bare venv, and verify the T-0142/T-0152 dependency completeness holds there too); (6) final release gate: frob check exit 0 with gates at zero, frob sys audit fully PROVED, full pytest suite green, drift-locks all live. Do not tag or publish -- leave the repo in a provably releasable state and report what the release command sequence would be.

<!-- ticket:T-0157 -->
```yaml
id: T-0157
title: 'secrets-scan gate: real-looking API tokens in tracked files fail check unless
  marked fake'
state: queued
kind: security
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/check/**
- tests/**
- docs/modules/gates.md
- frob.toml
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: info-disclosure
```
New gate family: scan TRACKED files (git ls-files, never untracked/.env -- and a TRACKED .env is itself a critical finding) for real-looking API tokens and credentials; any match fails frob check unless the site is explicitly marked fake. INVESTIGATE FIRST: the existing frob:secret directive in the comment DSL -- build on its semantics (e.g. frob:secret fake annotation) rather than inventing a parallel marker; also honor obvious placeholder shapes (XXXX runs, asterisks, the literal words fake/changeme/example/placeholder inside the token) so docs and tests stay writable. Pattern table, named per provider with SPECIAL ATTENTION to: OpenAI (sk- and sk-proj- prefixed), Anthropic (sk-ant-), Stripe (sk_live_/rk_live_/pk_live_/whsec_ -- pk_test/sk_test count as real-looking too, flag at lower severity), and finance/common services: AWS (AKIA/ASIA access ids + paired 40-char secrets), GitHub (ghp_/gho_/ghs_/ghu_/github_pat_), GitLab (glpat-), Slack (xoxb-/xoxp-/xoxa-/xoxs-), Google (AIza...), Twilio, SendGrid (SG.), Plaid, Square (sq0), PayPal/Braintree, npm (npm_), PyPI (pypi-), HuggingFace (hf_), private-key PEM blocks (BEGIN ... PRIVATE KEY), and JWTs (eyJ header heuristic). Each pattern carries provider name, severity, and a format constraint (length/charset/checksum where the format has one) to cut false positives; generic high-entropy fallback only if it can be made honest (document the false-positive class per T-0151 precedent, or omit with written reasoning). CRITICAL implementation constraints: (1) NEVER echo the full matched token in any output, log, or ticket -- redact to provider + prefix + length; (2) the gate's own tests need realistic-SHAPED tokens: construct them clearly fake (e.g. correct prefix + XXXX/pattern-invalid tail) and/or annotate with frob:secret fake so the gate does not fail its own fixtures (T-0151 self-match lesson -- lock this with an explicit test that the test files themselves pass the gate); (3) wire into frob check as a default-on gate with its own rule ids and a waive path requiring a written reason; (4) run the new gate against the whole current repo and make it green honestly -- if anything real-looking is already tracked, that is a finding to surface loudly in the Done report, not to quietly waive. Drift-lock: a provider listed in the pattern table without a fixture exercising it fails the suite.

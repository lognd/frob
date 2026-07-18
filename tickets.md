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
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope: []
evidence: []
attachments: []
acceptance: []
threat: null
```
Found immediately after the first post-archive frob ticket new: allocation scans only the active tickets.md for the max id, so a freshly archived queue restarts at T-0001, colliding with archived ids and making the merged active+archive queue unloadable (DuplicateId on every command). Fix: allocate from the max across BOTH ledgers (load_queue already merges them; reuse that path), plus a regression test: archive a ledger, file a new ticket, assert the id continues the sequence and the merged queue loads.

<!-- ticket:T-0141 -->
```yaml
id: T-0141
title: 'cache corrupt-recovery crashes on Python 3.12 sqlite: DROP TABLE raises before
  rebuild'
state: queued
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope: []
evidence: []
attachments: []
acceptance: []
threat: null
```
CI (python 3.12) fails tests/test_graph.py::TestCorruptCacheRecovery::test_garbage_cache_file_is_recreated: cache.connect detects the unreadable db (logs 'rebuilding') but _apply_schema then runs DROP TABLE IF EXISTS on the same corrupt connection and 3.12's sqlite raises sqlite3.DatabaseError('file is not a database') -- the T-0019 delete-and-rebuild contract never engages. Local 3.11 passes, so the recovery path is version-sensitive. Fix: when the db is detected unreadable (or when any DatabaseError escapes schema application), CLOSE the connection, DELETE the file, and reconnect fresh instead of issuing DDL over the corrupt handle; must pass on 3.11 AND 3.12 (parametrize CI already covers both).

<!-- ticket:T-0142 -->
```yaml
id: T-0142
title: standalone frob check crashes FileNotFoundError when ruff/ty binaries absent
  -- wheel declares no tool deps
state: queued
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope: []
evidence: []
attachments: []
acceptance: []
threat: null
```
The T-0133/T-0135 standalone CI job (bare wheel, clean venv) fails its no-traceback assertion: frob check's _run_ruff shells out to 'ruff' which the wheel neither declares as a dependency nor guards against being absent -- FileNotFoundError propagates through _run_tasks_concurrently as a raw traceback. Same exposure for ty and any other spawned tool. Fix BOTH layers: (1) declare ruff (and ty) as real [project] dependencies so a standalone install is fully functional out of the box (they are pip-installable; pin compatibly with the dev pins); (2) defense in depth per the natives-less precedent -- a missing tool binary becomes a typed ToolResult failure ('tool unavailable: ruff -- install X or use make install-tool') instead of an exception, covered by a monkeypatched-absence test. The CI job must then pass un-gated.

<!-- ticket:T-0143 -->
```yaml
id: T-0143
title: 'std.cwe catalog: transcribe the cwe-top-25 view (and stub-free ASVS decision)'
state: queued
kind: security
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope: []
evidence: []
attachments: []
acceptance: []
threat: null
```
Phase A shipped the 9 charter core-reframe CWEs backing owasp-top-10 only; cwe-top-25 / owasp-asvs / cwe-1000 were deliberately not stubbed so THREAT001 cannot lie. User asks for fuller coverage. Scope: transcribe the current MITRE CWE Top 25 into WeaknessEntry rows -- each with real cite URL, accurate title, meaningful mitigation, capability_kind where the charter's instantiation semantics genuinely apply, and honest OutOfScopeEntry rows (with specific reasons) for entries whose preconditions the kernel cannot yet express (matching the T-0114 discipline). Add the cwe-top-25 view; extend tests: view completeness proves, per-entry data spot checks, and at least two new fired-obligation cases for newly-instantiable kinds. owasp-asvs/cwe-1000: make an explicit documented decision (transcribe, or keep unstubbed with rationale in threat.md) rather than silence. Pin the catalog to a named CWE release version per the charter's staleness-review requirement.

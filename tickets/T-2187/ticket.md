---
id: T-2187
title: 'walk_strata parses .strata with the strata-core grammar then discards it,
  extracting symbols by line regex instead and downgrading the disagreement to a log
  warning: 16 mismatches in a single run'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: T-1662
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/lang/_walk_strata.py
- tests/unit/test_lang_strata.py
evidence_scope:
- tests/unit/test_lang_strata.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_lang_strata.py
  reason: T-2187's own repro/regression tests live here, alongside every other .strata
    walker test
  actor: logan
  at: '2026-08-16'
evidence:
- tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_quoted_string_claim_id_is_extracted
- tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_resource_declaration_is_extracted
- tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_locator_fails_closed_on_a_construct_it_cannot_find
- tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_walk_strata_returns_err_not_a_log_line_on_disagreement
- tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_declared_items_covers_every_keyword_family
designated_repro_test: tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_quoted_string_claim_id_is_extracted
acceptance:
- text: 'Symbols MUST come from strata-core''s parse result, not from _HEADER_RE over
    source lines. walk_strata (src/frob/lang/_walk_strata.py) already calls strata_core.parse_source(source)
    and has the authoritative grammar output in parsed[''ok''], then throws it away:
    _extract_symbols(lines) produces the symbols actually returned, and _check_declared_count_drift
    only LOGS when the two disagree. Measured: 16 ''header-regex symbol count != strata-core
    declared count'' warnings in a single frob verify explain run. This test MUST
    fail against current main.'
  evidence:
  - tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_quoted_string_claim_id_is_extracted
- text: Given a .strata source where the grammar and the header regex disagree on
    symbol count, when walk_strata runs, then the returned symbols match the grammar's
    declarations -- not the regex's. Today the regex result is returned and the mismatch
    is a warning the caller never sees.
  evidence:
  - tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_resource_declaration_is_extracted
- text: 'Do NOT fix this by tightening _HEADER_RE until the counts agree on today''s
    corpus -- that is a lexical fix to a lexical defect and the next construct reopens
    it. Do NOT delete the drift check either: keep it, but it should be a fail-closed
    disagreement between the grammar and any remaining heuristic, never a silent log
    line. Note strata symbols feed capability enforcement, which T-1623 (critical)
    is separately trying to make watertight -- a wrong symbol set undermines that
    gate silently.'
  evidence:
  - tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_walk_strata_returns_err_not_a_log_line_on_disagreement
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Done report

Changed:
- src/frob/lang/_walk_strata.py -- symbols now come from strata-core's
  own structured parse (`_declared_items`, the grammar's authoritative
  `(keyword, id)` list), not from `_HEADER_RE` guessing what exists.
  `_HEADER_RE` is replaced by `_KEYWORD_ONLY_RE` (recognizes only the
  leading keyword token, no identifier-capture group) plus
  `_locate_declared_items`, which LOCATES each grammar-declared
  construct's own span by matching the REST of a header line against
  that construct's exact `id`/`target` text (bare identifier or quoted
  string literal, per `_rest_starts_with_id`). A declared construct the
  locator cannot find fails the whole walk closed (`walk_strata` returns
  `Err`), replacing the old `_check_declared_count_drift` warning-only
  log line. `resource` (present in `_KEYWORD_KIND`/keyword vocabulary for
  the first time -- 3 real declarations in this repo's own corpus were
  previously invisible to this walker entirely) and `claims`
  (assert/assume, keyed by the `assumed` bool) are now covered.
- tests/unit/test_lang_strata.py -- new `TestGrammarAuthoritativeSymbols`
  class: two minimal repros of the measured defect (a quoted-string claim
  id, a `resource` declaration), a fail-closed unit test on
  `_locate_declared_items` directly, an integration test that
  `walk_strata` returns `Err` (not a log line) on a forced disagreement,
  and a `_declared_items` keyword-family coverage test.

Root cause (measured directly against this repo's real `.strata` corpus,
64 tracked files): `_HEADER_RE`'s identifier-capture group
(`[A-Za-z_][A-Za-z0-9_]*`) can never match a quoted-string claim id --
`assume "weakness:CWE-78:claude_hooks" noflow ...` is real syntax (32 of
34 claims in design/frob.strata alone use a quoted string id, not a bare
identifier) -- and `resource` was entirely absent from the keyword
vocabulary despite being declared 3 times in the corpus. Both silently
undercounted; the drift check only logged a WARNING the caller never saw.

Symbol-set delta, full real corpus (measured, not estimated -- old
main-branch code vs the fix, same 64 files, same content):
- 16 of 64 files change; 48 remaining files are byte-identical in symbol
  count and qualname set (this fix is not a blanket rewrite -- the large
  majority of the corpus already reconciled correctly).
- 430 -> 479 total symbols (+49). EVERY changed file is a pure ADDITION
  (a symbol that was silently invisible before now correctly appears) --
  zero symbols were ever removed, so the old regex never fabricated an
  extra symbol, only missed real ones. Full per-file diff (added
  qualnames) is in the ticket's own history; design/frob.strata alone
  gained 30 previously-invisible claim symbols.

Consumer relationship (T-1623 context, correcting the coordinator's
framing where it does not hold, per this session's own "say so with
evidence" instruction):
- `walk_strata`'s RawSymbol/RawComment output feeds `frob.lang.
  parse_file` -> `frob.graph`'s cross-language snapshot for every
  `.strata` file -- this is the REAL, LIVE consumer this fix changes.
  Before this fix, none of the 49 newly-visible symbols (mostly
  `assert`/`assume` claims) existed in `frob.graph` at all for those 16
  files, so a `frob:doc`/`frob:tests` coverage obligation on any of them
  could never even be EVALUATED (silently absent from the obligation
  graph the COV/TEST/DUP/xref gate families walk) -- not a wrong answer,
  an unasked question. That gap is now closed.
- SYS100-104 capability enforcement itself (T-1623's actual target,
  `check_self_conformance`/`DesignIds`/`KernelModel`) consumes
  `frob.strata._parse.parse_module` DIRECTLY (`src/frob/strata/
  _design_load.py:37,224`) -- a separately-implemented, always-typed,
  always-grammar-correct path (it also calls `strata_core.parse_source`,
  but never routes through `_HEADER_RE`/`walk_strata` at all). This path
  was NEVER affected by this defect; T-1623's own capability-declaration
  facts were correct on main before this fix and remain correct after
  it -- verified by reading `_design_load.py`'s imports, not assumed.
  `check_self_conformance` was run as part of this ticket's own
  regression pass (test_selfconform.py, test_conform_eval_needle.py,
  test_design_load.py) and shows no change from this fix.
- The one place these two paths intersect: `frob.strata._effects.py::
  _symbols_for_file` calls `frob.lang.parse_file` (hence `walk_strata`
  for a `.strata`-extension target) to resolve a `may "capability" via
  "SYMBOL-FORM"` clause's symbol-form target. This repo's own
  `design/frob.strata` has zero `via "*.strata"` clauses today (checked:
  `grep 'via "' design/frob.strata` has no `.strata`-suffixed target) --
  a real but currently DORMANT connection, not a live effect on any
  measured T-1623 capability-enforcement gap today. Worth T-1623 knowing
  about if a future `.strata`-targeted `via` clause is ever added.
- Net: this fix does not change any SYS10x capability-enforcement
  verdict measured today (confirmed by running the self-conformance
  suite), but it DOES change what `frob.graph`'s doc/test-coverage gates
  can see for 16 `.strata` files, and that is real, previously-invisible
  surface T-1623 (or a coverage-focused follow-up) should know exists as
  of this ticket landing.

Prohibitions honored:
- `_HEADER_RE` was NOT tightened as the fix mechanism -- it is replaced
  by a keyword-only recognizer (`_KEYWORD_ONLY_RE`) that decides nothing
  about identity; the grammar's own declared id text (bare or quoted) is
  what `_locate_declared_items` matches against, verbatim, never a
  smarter identifier pattern.
- The drift check was kept, not deleted -- `walk_strata` still checks
  grammar-vs-locator agreement on every call, now fail-closed (`Err`)
  instead of log-and-continue.

Evidence:
- tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_quoted_string_claim_id_is_extracted
  (designated repro, T-2187's acceptance [0]: `--check-repro` verified
  FAILED_AT_PARENT against e86cdfbc9 -- the test-only commit, unfixed
  code -- per the T-2021 technique docs/modules/tickets.md#check-repro-post-land-limitation-t-2025
  documents for a brand-new test with no pre-existing main history).
- tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_resource_declaration_is_extracted
- tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_locator_fails_closed_on_a_construct_it_cannot_find
- tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_walk_strata_returns_err_not_a_log_line_on_disagreement
- tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_declared_items_covers_every_keyword_family
- `uv run pytest tests/unit/test_lang_strata.py`: 26 passed (was 22
  before this ticket's 5 new tests; existing tests unchanged, including
  chirp.strata's own symbol/span/doc-comment assertions).
- `uv run pytest tests/unit/strata/test_litmus_chirp.py tests/unit/strata/test_litmus_cwe.py tests/unit/strata/test_litmus_pii.py tests/unit/strata/test_litmus_utility_hub.py tests/unit/strata/test_managed.py tests/unit/strata/test_design_load.py tests/unit/strata/test_selfconform.py tests/unit/strata/test_multifile.py`:
  139 passed.
- `uv run pytest tests/unit/strata/test_effects.py tests/unit/strata/test_audit.py tests/unit/strata/test_contention.py tests/unit/strata/test_parse.py tests/unit/strata/test_facts.py`:
  145 passed (test_contention.py exercises `resource` declarations
  directly).
- `uv run pytest tests/test_graph.py`: 128 passed.
- `uv run pytest tests/unit/graph/`: 73 passed.
- `uv run pytest tests/unit/strata/test_conform_eval_needle.py` (the
  SYS100 self-conformance real-repo check): 6 passed -- confirms zero
  change to capability-enforcement verdicts.
- Manual full-corpus measurement (not a checked-in test -- would require
  new `subprocess`/`read_text` effects in the test file that this
  ticket's own design/frob.strata scope does not declare; see below):
  all 64 tracked `.strata` files walk with zero `Err` under the fix
  (were 16/64 disagreeing, silently, under the old code).
- `uv run frob check --ticket T-2187 --only gates-fast/gates-native/gates-security/lint`:
  zero findings on `src/frob/lang/_walk_strata.py` or
  `tests/unit/test_lang_strata.py`. One pre-existing, unrelated
  ruff-check E501 elsewhere (`_land_cmd.py:3354`) and pre-existing
  `.strata` `frob fmt` debt (50 files, none touched by this ticket) were
  observed and are explicitly NOT this ticket's scope.

Filed: none new. (Considered adding a permanent full-corpus regression
test to this ticket's own test file, but `subprocess.run`/`.read_text()`
calls there trip `frob.strata._effects.py`'s SYS100 self-conformance scan
for the `tests/unit/test_lang_strata.py::testsuite` node -- fixing that
would require a `design/frob.strata` edit, outside this ticket's declared
scope (`src/frob/lang/_walk_strata.py`, `tests/unit/test_lang_strata.py`).
Manual verification above covers the same ground; a follow-up ticket
scoped to `design/frob.strata` could add the permanent corpus-wide guard
if wanted.)

Gates: clean on this ticket's own files (`--ticket T-2187`, all four
groups above). `frob fmt` debt on 50 unrelated `.strata` fixture files
pre-exists this ticket and is untouched.

### Changed
```
 src/frob/lang/_walk_strata.py  | 233 +++++++++++++++++++++++++++++++++--------
 tests/unit/test_lang_strata.py | 161 +++++++++++++++++++++++++++-
 tickets/T-2187/ticket.md       |  20 +++-
 3 files changed, 365 insertions(+), 49 deletions(-)
```

### Evidence
- `tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_quoted_string_claim_id_is_extracted` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_resource_declaration_is_extracted` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_locator_fails_closed_on_a_construct_it_cannot_find` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_walk_strata_returns_err_not_a_log_line_on_disagreement` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbols::test_declared_items_covers_every_keyword_family` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/lang/_walk_strata.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2187/src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2187/src/frob/lang/_walk_strata.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2187, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md

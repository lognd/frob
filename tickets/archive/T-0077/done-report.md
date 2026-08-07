## Done report

Design decision: there is no `tree-sitter-strata` grammar, so `.strata`
cannot go through `frob.lang`'s tree-sitter `_parse`/`extract` pair the
other five grammars share. `parse_file` now special-cases the `.strata`
extension (checked before the tree-sitter dispatch) and routes it through
a new `frob.lang._walk_strata.walk_strata`, which reuses strata-core's own
parser (`strata_core.parse_source`, the Rust crate's Python binding) as
the sole correctness oracle for *which* top-level constructs a file
declares -- a parse rejection from strata-core becomes `Err` before any
regex ever runs, so this walker never fabricates symbols for invalid
strata. strata-core's structured JSON output carries no line-span
information (kernel facts are span-free by design per docs/strata/kernel.md),
so spans are recovered by a regex-driven line scan (`_HEADER_RE` over
strata-core/src/parse.rs's real top-level keyword table: module, node,
store, queue, cache, cdn, balancer, boundary, flow, assert, assume,
refine, policy, operation, scenario) paired with brace-balance matching
for block-delimited constructs. `walk_strata` cross-checks the regex-
derived symbol count against strata-core's own declared-construct count
and logs a warning on mismatch, as a drift trip-wire in case the header
regex ever falls out of sync with the real grammar. Both the tree-sitter
comment-binding logic and the new strata comment-binding logic now share
one implementation (`find_enclosing_symbol`/`find_following_symbol`,
promoted from `_extract.py` private duplicates into `_common.py` public
helpers) rather than keeping two copies.

Kind mapping (no natural fit exists for design constructs in a
function/class/const/type vocabulary, so this is a best-effort analogy):
module/node/store/queue/cache/cdn/balancer -> CLASS (containers/infra),
boundary/flow -> FUNCTION (edges/contracts), assert/assume -> CONST
(static facts), refine/policy -> TYPE (relationships), operation/scenario
-> METHOD (invocable behaviors). Every strata symbol is `public=True` --
the language has no privacy concept. Qualnames are module-prefixed
(`chirp.tweets_hot`) once a `module` decl has been seen.

`extract_imports`, `iter_identifiers`, `raw_tree`, and `symbol_tree` stay
`Err(UnsupportedLanguage)` for `.strata` paths -- they are tree-sitter
`Node`-level escape hatches (`frob.arch`'s structural walks, `frob.dup`'s
R4 tree-edit-distance rung) with no `.strata` analogue yet, documented as
a deliberate scope boundary rather than an oversight.

Changed:
- src/frob/lang/__init__.py (`.strata` dispatch in `parse_file`, new
  `_parse_strata_file`/`_build_parsed_file`, `_STRATA_EXTENSION`/
  `_STRATA_LANGUAGE`, `_SUPPORTED_LANGUAGES` now includes `"strata"`)
- src/frob/lang/_walk_strata.py (new: the strata walker)
- src/frob/lang/_common.py (`find_enclosing_symbol`/`find_following_symbol`
  promoted to public, shared helpers)
- src/frob/lang/_extract.py (drops its now-duplicate `_find_enclosing`/
  `_find_following`, imports the shared `_common.py` versions instead)
- tests/unit/test_lang_strata.py (new: 14 tests)

Evidence (frob:tests-bound, `frob ticket evidence` recorded 5 representative
node ids; full set below all pass under `uv run pytest`):
- tests/unit/test_lang_strata.py (14 tests: kind mapping, module-qualified
  qualnames, public=True, multi-line vs single-line spans, leading-comment
  doc_text, comment enclosing/following binding, content-hash stability,
  parse-failure -> `LangError.ParseFailed`, `walk_strata` direct Err path,
  and the three tree-sitter-escape-hatch-stays-unsupported cases)
- tests/test_lang.py, tests/unit/test_lang_primitives.py,
  tests/unit/strata/**, tests/test_graph.py -- all green, no regressions
- `uv run pytest` (full suite): green
- `uv run ruff check`/`ruff format` on touched files: clean
- `uv run ty check src/frob/lang/`: clean
- `uv run frob test --base main`: touched-set selection green (exit=0)

Verify-step findings (step 6 of the assignment):
- `parse_file`/`extract` on `.strata` work end to end: 17/27/29/20 symbols
  extracted from design/litmus/{chirp,payments,payments_hardened,tube}.strata
  respectively, matching strata-core's own declared-construct counts (no
  drift warning fired).
- The "no grammar registered for extension '.strata'" WARNING noise for
  design/litmus/*.strata does **not** fully disappear from `frob check`.
  Root cause: `frob.arch._analyze_one_file` (src/frob/arch/__init__.py)
  calls `raw_tree` on every collected file with no extension guard at all
  -- `raw_tree` is a tree-sitter-only escape hatch that correctly returns
  `UnsupportedLanguage` for `.strata` (see design decision above), and
  `frob.graph`, `frob.outline`, `frob.xref`, `frob.testing._select`, and
  `frob.policy` each filter files through their own hand-duplicated
  extension table rather than `frob.lang.supported_languages()`, so none
  of them discover `.strata` either. All of those files
  (src/frob/arch/__init__.py explicitly, the rest implicitly via "do not
  expand scope") are outside T-0077's declared scope
  (src/frob/lang/**, src/frob/strata/**, tests/**). Filed T-0129 to wire
  them up.
- `frob map`/`frob outline` on a `.strata` path do not yet work --
  `frob.outline.outline_file` dispatches by its own suffix check rather
  than `frob.lang.parse_file`; covered by T-0129.

Filed: T-0129 (wire `.strata` into frob.graph/outline/xref/testing/policy/
cycle_runner/arch's raw_tree call so map/outline/xref/COV obligations
reach `.strata` symbols end to end -- out of T-0077's scope).

Gates: `frob check --ticket T-0077` shows zero new COV001/TEST001-006/
DRIFT/SYS diagnostics attributable to this change (the one COV001 hit
inside `frob.lang` is `_extract.py::COMMENT_TYPES`, pre-existing before
this ticket, confirmed via `git show df83377:src/frob/lang/_extract.py`).
Repo-wide `frob check`/`gates` still FAIL, but only from pre-existing
violations across files this ticket never touched (this worktree has a
concurrent agent actively modifying unrelated files -- docs/commands/check.md,
docs/modules/gates.md, src/frob/__main__.py, src/frob/app/check_runner.py,
src/frob/app/config.py, tests/system/test_cli_check.py -- left untouched
here). frob-arch's `long-function` heuristic (threshold 30 lines) briefly
flagged `walk_strata`/`_parse_strata_file`/`parse_file`; refactored via a
shared `_declared_count`/`_reject`/`_build_parsed_file` extraction so all
three are back under 30 lines (frob-arch is advisory/non-blocking either
way, but keeping it clean avoids adding to the pile).

## Post-review update: T-0100 merge reconciliation

Reviewer REJECTed the first pass with a CRITICAL finding: this worktree's
`_extract.py` predated two T-0100 amendments (stacked-directive block
binding, commit `8e0b8f7`, and the trailing-comment fix that was still
uncommitted/in-flight at review time) that live on branch
`worktree-agent-ad138df9db0bab491` (commit `f50fb50`), not on git `main`
(git `main` is still at `d04e52f` in this environment -- the T-0100 fix
has not landed there yet; "current main" for reconciliation purposes meant
that worktree's branch, confirmed by locating the actual
`_is_trailing_comment`/`_block_ends`/block-aware `_extract_comments` code
there). My original `find_enclosing_symbol`/`find_following_symbol`
promotion into `_common.py` had lifted only the pre-T-0100 span-comparison
logic and dropped the block-aware call site, which would have reverted the
trailing-comment fix on merge.

Fix, per protocol (commit-then-merge, no `git stash` -- this shared
worktree environment has already lost work twice to `git stash` racing
concurrent agents; see the original Done report above):
1. `git add -A && git commit -m "wip: T-0077 strata grammar before main
   merge"` (commit `92021bf`).
2. `git merge worktree-agent-ad138df9db0bab491 --no-edit` -- two
   conflicts: `src/frob/lang/_extract.py` and `tickets.md`.
3. `_extract.py`: took the T-0100 branch's version in full (`git show
   worktree-agent-ad138df9db0bab491:src/frob/lang/_extract.py`), which
   restores `_is_trailing_comment`, `_block_ends`, and the block-aware
   `_extract_comments` (calls `_find_following((span[0], block_end),
   symbols)` instead of the comment's own span) verbatim. Reapplied only
   the promotion: import `find_enclosing_symbol`/`find_following_symbol`
   from `_common.py` in place of the two local defs. This is safe because
   both local defs were byte-identical in logic to what `_common.py`
   already held (`_common.py` itself never conflicted -- the T-0100 branch
   never touched it, so my promotion survived the merge untouched; only
   verified the two functions' bodies matched before deleting the
   duplicates). `_common.py`'s `find_following_symbol` docstring was
   extended to explain the block-vs-own-line distinction is the caller's
   concern (T-0100's nuance lives entirely in `_extract.py`'s
   `_block_ends`/`_is_trailing_comment`, which are tree-sitter-`Node`-
   specific and were never candidates for promotion to the strata-shared
   layer in the first place -- strata's own `_walk_strata._extract_comments`
   only ever emits whole-line comments with no trailing-comment concept,
   so it never needed block-end chaining).
4. `tickets.md`: two conflict hunks, both from concurrent `frob ticket
   new` collisions on the same next-available ID slot. Kept the T-0100
   branch's `T-0126` (done, COV001 fix) and `T-0127` (queued, DOC002-style
   doc-anchor gate) as authoritative, and renumbered my own new ticket from
   its original `T-0126` (already fixed to `T-0128` before this merge,
   per the original Done report above) up again to `T-0129` to clear the
   second collision. Updated every in-report reference from `T-0128` to
   `T-0129` accordingly.
5. Verified: `tests/test_graph.py::TestDsl::test_directive_binds_past_trailing_comment_on_def_line`,
   `test_stacked_directives_bind_past_trailing_comment_on_def_line`,
   `test_binds_three_stacked_directives_to_def`,
   `test_binds_five_stacked_directives_to_def` (all `TestDsl`, 20 tests)
   pass, alongside all 14 `tests/unit/test_lang_strata.py` tests and the
   rest of `tests/test_lang.py`/`tests/unit/test_lang_primitives.py`/
   `tests/unit/strata/`. Full `uv run pytest` (whole repo): green, no
   regressions. `uv run ruff check`/`ty check` on `src/frob/lang/`: clean.
   `frob check --ticket T-0077` after the merge: zero COV001/TEST001-6/
   DRIFT/SYS diagnostics under `src/frob/lang/` (grep-verified against the
   full check log).

Merge commit: `2a38519` ("Merge branch 'worktree-agent-ad138df9db0bab491'
into worktree-agent-a992dbcf025c79b08"), on top of wip commit `92021bf`.
Neither T-0077 nor T-0129 closed; nothing pushed; no further commits made
beyond the two required for the merge.

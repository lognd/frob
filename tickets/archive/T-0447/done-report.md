## Done report

Changed:
- frob-core/src/lib.rs :: is_numeric_literal (new)
- frob-core/src/lib.rs :: is_string_literal (new)
- frob-core/src/lib.rs :: r3_canonicalize (new)
- frob-core/src/lib.rs :: r3_canonical_hash (now canonicalizes before folding)
- src/frob/dup/_pipeline.py (module docstring deviations note updated to
  describe the T-0447 R3 fix; no function bodies changed -- the
  canonicalization moved into the Rust kernel per the ticket title)
- tests/test_dup.py (new file: TestR3LiteralAbstraction,
  TestR3ElifDesugar, TestCrossLanguageR5Litmus)
- frob-core/src/lib.rs unit tests: r3_literal_abstraction_collapses_differing_constants,
  r3_literal_abstraction_does_not_collapse_different_operators,
  r3_elif_desugar_matches_manually_nested_if_else,
  r3_elif_desugar_does_not_collapse_different_conditions,
  is_numeric_literal_rejects_identifiers_and_keywords,
  is_string_literal_requires_matching_quotes

Implementation: `r3_canonical_hash` previously folded the exact same
R2-normalized token stream R2 hashes (the T-0199 finding recorded in
`docs/modules/dup.md` and `frob.dup._exhaustiveness.DUP_MATRIX_EXCUSES`).
`r3_canonicalize` now applies two real, tractable-without-an-AST token
transforms before folding: (1) literal abstraction -- numeric- and
string-literal-shaped tokens collapse to `_lit_num`/`_lit_str`; (2) `elif`
control-flow desugar -- `elif` (real syntactic sugar for `else: if`)
expands to `["else", ":", "if"]` before folding. Commutative-operand
reordering and real for/while loop-shape desugaring still need AST
structure, not a token fold, and are NOT implemented -- documented in both
the Rust docstrings and `_pipeline.py`'s deviations note, and not filed as
follow-up work (T-draft-82caf099 (never refiled)).

Fixture matrix (tests/test_dup.py, real `find_clones` pipeline, no
hand-built symbol records):
- TestR3LiteralAbstraction: `offset_by_one`/`offset_by_two` (differ only
  by `+ 1` vs `+ 2`) -- r2 does NOT bucket them (literal token differs),
  r3 DOES (literal abstracted). Negative: `offset_by_one` vs
  `offset_by_subtracting` (`+` vs `-`) -- r3 correctly does not merge.
- TestR3ElifDesugar: `classify_with_elif` (if/elif/else) vs
  `classify_nested` (manually nested if/else:if/else) -- r2 misses, r3
  fires via elif desugar. Negative: `classify_with_elif` vs
  `classify_different_condition` (`<` vs `<=` in the elif clause) -- r3
  correctly does not merge.
- TestCrossLanguageR5Litmus: `sum_py`/`sum_rs`, a bare `return a + b` in
  Python and Rust -- r1/r2/r3 do not fire (disjoint lexical vocabulary,
  same limit `tests/test_dup_cross_lang.py` already characterizes), r5
  fires (WL-hash over `_real_dataflow_graph`'s structural def/use labels,
  language-agnostic by construction). The fixture deliberately avoids a
  `let`/assignment statement -- a separate, real gap
  (`frob.dup._pipeline._KEYWORDS` is python-centric, so Rust's `let`
  keyword is misread as an identifier and mis-labeled "def", diverging
  the graphs) is out of scope and not filed as T-draft-82caf099 (never refiled) rather than
  fixed here.

Test results:
- `cargo test --manifest-path frob-core/Cargo.toml --lib` (with
  `PYO3_PYTHON=<worktree>/.venv/bin/python3.11`,
  `LD_LIBRARY_PATH=/home/logan/.local/share/uv/python/cpython-3.11.15-linux-aarch64-gnu/lib`):
  `test result: ok. 39 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out`
- `uv run pytest tests/test_dup.py tests/test_dup_rungs.py
  tests/test_dup_exhaustiveness.py tests/test_dup_cross_lang.py
  tests/test_dup_r5_multilang.py tests/test_dup_smart.py
  tests/test_dup_prefilter.py tests/test_dup_region.py
  tests/test_dup_inline.py -q`: all green (measured directly, xdist
  summary `........................................................................ [78%]` then
  `....................                                                     [100%]`, 0 failures).
- `uv run pytest tests/test_dup.py --collect-only -q -o addopts=""`
  resolves all 7 node ids used as evidence below.

Not Filed: T-draft-82caf099 (never refiled) (python-centric `_KEYWORDS` misclassifies
rust/ts/c/cpp declaration keywords as identifiers in R5 def-use labeling;
also notes the remaining R3 deviations and the
`frob.dup._exhaustiveness.py` DUP_CLAIMS/DUP_MATRIX_EXCUSES update this
ticket's fix unlocks, both out of T-0447's declared scope).

Gates: `uv run frob check --ticket T-0447` -- after `uv run frob ticket
sweep T-0447` to refresh the stale PRE001 pre-work snapshot and `uv run
ruff format tests/test_dup.py`, the only remaining unwaived line is
`TEST006: no coverage stamp found; run: make coverage` against
`.frob/coverage-stamp` -- a repo-wide, worktree-local artifact (no
`.frob/coverage-stamp` exists in this fresh worktree at all) unrelated to
this ticket's scope/changes, not something `frob-core/src/lib.rs` /
`_pipeline.py` / `tests/test_dup.py` changes can produce or fix. No
`archgate`/`gates` ERROR-level violation is unwaived. `git diff main
--diff-filter=D --stat` is empty (no deletions).

## Done report

frob.dup._pipeline._KEYWORDS was hand-listed and python-only, so a Rust
`let` (or a TypeScript `interface`, a C `struct`, etc.) matched
`_IDENT_RE` and was never excluded from R2's alpha-rename set or R5's
def-use labeling (`_labeled_ids`/`_add_chunk_nodes`), mis-labeling the
keyword as an extra def/use identifier node and skewing cross-language
fingerprints. Fixed by unioning the existing python-only pseudo-keyword
set (`with`/`as`/`is`/`None`/`self`/... -- spellings with no cross-grammar
counterpart) with `frob.lang._common._CANONICAL_VOCAB`'s keys, the
pooled keyword/punctuation-spelling table `_BLOCK_LABELS`/
`_ASSIGNMENT_LABELS` already mirror this per-grammar-pooled-into-one-set
pattern for -- no second hand-maintained per-language keyword list.

Verified the fix directly: `_KEYWORDS` now recognizes `let`, `fn`,
`struct`, `impl`, `match`, `switch`, `case`, etc. across every
`frob.lang` grammar. Added a regression fixture
(TestCrossLanguageR5WithLet in tests/test_dup.py) with a Rust `let`
binding on one side and a Python assignment on the other -- R5 now
correctly WL-hash-collides the two (previously the spurious `let` def
node would have diverged the graphs); this is a real, verified positive
(also directly confirmed via `find_clones` at the REPL against the
existing dup_cross_lang python/typescript fixture -- R5 now correctly
fires there too, similarity=0.88).

Updated frob.dup._exhaustiveness per the ticket: T-0447 already landed
frob-core's r3_canonicalize (literal abstraction + elif desugar), so the
stale "r3 folds the same stream as r2" excuse is removed and replaced
with a DUP_CLAIMS entry proven by tests/test_dup.py's existing
TestR3LiteralAbstraction fixture. The r5/rust cell also gets its own
DUP_CLAIMS entry (proven by the new with-let fixture above), replacing
its generic non-python language-gap excuse; `_non_python_excuses()` now
skips any (rung, clone_type, language) cell already covered by a
DUP_CLAIMS entry so a claimed cell is never also auto-excused.

Bumped pyproject.toml to 0.37.0 and ran `frob release stamp`
(DUP_CLAIMS/DUP_MATRIX_EXCUSES content is public API; REL001 flagged the
change as major). Note: main advanced to 0.37.0 independently while this
ticket was in flight (another ticket's own release stamp); the
post-merge version and .frob-release.json both already matched, no
conflict.

Filed T-draft-413001ba (out of this ticket's declared scope): the
keyword fix makes R5 now correctly fire cross-language for the EXISTING
tests/fixtures/dup_cross_lang python/typescript pair (mod_a.py's
compute_total vs mod_b.ts's computeTotal use a `let`), which breaks
tests/test_dup_cross_lang.py::TestCrossLanguageCloneNotYetDetected::test_no_clone_group_at_any_threshold's
"zero groups at every threshold" characterization assertion (5
parametrized cases). This is a real accuracy improvement, not a
regression, but that test file is not in T-0487's declared scope, so the
follow-up ticket covers updating its characterization instead of
silently patching it here. That one pre-existing test (5 parametrized
cases) is left red by this ticket's change; every other dup test
(tests/test_dup*.py, tests/unit/test_dup*.py) passes.

### Changed
```
 .frob-release.json              |   4 +-
 src/frob/dup/_exhaustiveness.py |  78 +++++++++++++++---------
 src/frob/dup/_pipeline.py       |  64 +++++++++----------
 tests/test_dup.py               |  62 +++++++++++++++----
 tests/unit/test_dup.py          |  40 ++++++++++++
 tickets.md                      | 132 +++++++++++++++++++++++++++++++++++++---
 6 files changed, 299 insertions(+), 81 deletions(-)
```

### Evidence
- `tests/test_dup.py::TestCrossLanguageR5WithLet::test_r5_fires_across_languages_with_a_let_binding` (pytest node id, verified passing when recorded)
- `tests/test_dup.py::TestR3LiteralAbstraction::test_r3_fires_where_r2_does_not` (pytest node id, verified passing when recorded)
- `tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_no_unclaimed_cells` (pytest node id, verified passing when recorded)
- `tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_no_cell_is_both_claimed_and_excused` (pytest node id, verified passing when recorded)

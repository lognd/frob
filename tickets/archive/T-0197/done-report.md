## Done report

Changed:
- src/frob/dup/_pipeline.py -- three additive R4 candidate pre-filters,
  wired into `_r4_candidate_pair` right before the expensive
  `_r4_verify_pair` (statement-alignment + APTED) call:
  - `_nicad_size_ratio_ok` (docs/modules/dup-sota-survey.md item 2's one
    adoptable idea): token-count ratio gate.
  - `_oreo_metric_ratio_ok` (item 6, non-ML half): branch-keyword-count
    ratio gate (`_BRANCH_KEYWORDS`), a cheap McCabe-complexity proxy,
    add-one smoothed so two zero-branch bodies never reject each other.
  - `_deckard_vector_ok` + `_characteristic_vector` + `_cosine_similarity`
    (item 4): a DECKARD-style characteristic vector over R2-normalized
    token-shape categories (all alpha-rename placeholders collapsed into
    one `"IDENT"` bucket, everything else -- keywords/punctuation/literals
    -- its own bucket), compared by cosine similarity. Real DECKARD builds
    this over per-subtree AST node-type labels; `frob.lang.RawSymbol
    .body_tokens` carries no per-token node-type metadata, so this uses the
    lexical-shape stand-in instead -- documented as a deviation in the
    module docstring, same posture as the existing R2/R3 deviation notes.
  - `_passes_r4_prefilters` ANDs all three; `cfg.prefilter_enabled=False`
    (default `True`) restores the pre-T-0197 behavior exactly (every R4
    LSH candidate reaches verification).
  - Per-symbol stats (`size_by_ref`, `metric_by_ref`, `vector_by_ref`)
    computed once in `_fingerprint_symbol` alongside the existing R1-R5
    bucketing, no extra parse pass.
  - `DupStats.pairs_prefiltered` counter added and logged in
    `_clone_report`, so a caller can see how much R4 verification work the
    pre-filters actually skipped without changing the reported groups.
- src/frob/dup/_models.py -- `DupStats.pairs_prefiltered: int = 0`;
  `DupConfig.prefilter_enabled: bool = True`,
  `prefilter_size_ratio: float = 0.25`, `prefilter_metric_ratio: float =
  0.15`, `prefilter_vector_similarity: float = 0.35` -- loose defaults
  chosen and verified (see Evidence) to leave every existing dup fixture's
  reported clone set unchanged.
- tests/test_dup_prefilter.py (new) -- unit tests on the three predicate
  functions plus `_characteristic_vector`/`_cosine_similarity` directly
  (no `frob_core` dependency), and parametrized recall-preservation tests
  over every existing dup fixture (`dup_smart`, `dup_rungs`, `dup_region`,
  `dup_inline`): `find_clones` with `prefilter_enabled=True` vs `=False`
  must report the EXACT same `(rung, left.ref, right.ref, similarity)` set
  -- this is the ticket's own instruction made into a gate, not just a
  spot check. Also asserts `pairs_verified` with prefilters on never
  exceeds `pairs_verified` with them off (pure pruning, never more work).

Verified NOT changed: `tests/test_dup_cross_lang.py` and
`tests/test_dup_r5_multilang.py` fixtures were intentionally left out of
the parametrized recall suite (T-0198's negative result means R1-R4 never
bucket that cross-language pair in the first place, so there is no R4
candidate for the prefilters to touch either way) -- re-ran both suites
directly instead to confirm no behavior change; both still pass unchanged
(7 + suite-specific passes, see Gates below).

Filed: none -- no out-of-scope work found.

Evidence: recorded via `frob ticket evidence T-0197 <node-id>...` (all 24
resolved against a fresh `pytest --collect-only -q -o addopts=` pass):
- tests/test_dup_prefilter.py::TestCharacteristicVector (3 tests)
- tests/test_dup_prefilter.py::TestCosineSimilarity (4 tests)
- tests/test_dup_prefilter.py::TestNicadSizeRatio (3 tests)
- tests/test_dup_prefilter.py::TestOreoMetricRatio (3 tests)
- tests/test_dup_prefilter.py::TestDeckardVector (3 tests)
- tests/test_dup_prefilter.py::TestPrefilterPreservesRecall::test_verified_clone_set_unchanged[dup_smart|dup_rungs|dup_region|dup_inline] (4 tests)
- tests/test_dup_prefilter.py::TestPrefilterPreservesRecall::test_prefilter_never_exceeds_unfiltered_verification_count[dup_smart|dup_rungs|dup_region|dup_inline] (4 tests)

Measured: `uv run pytest tests/test_dup_prefilter.py tests/test_dup_smart.py
tests/test_dup_rungs.py tests/test_dup_region.py tests/test_dup_inline.py
tests/test_dup_cross_lang.py tests/test_dup_r5_multilang.py -p
no:cacheprovider -q` -> all tests pass (24 new + full existing dup suite,
no failures, 2 skips are the pre-existing SMT-optional skips, unrelated to
this change).

Gates: `uv run frob check --ticket T-0197` clean -- `0 errors, 54 warnings,
25 waived` (all 54 warnings/25 waivers pre-exist on `main`, none newly
introduced by this ticket's files: `ruff-check`/`ruff-format`/`ty` all
`pass`; `frob-dup`, `frob-arch`, and every `frob-exports` check `pass`).
`PRE001` (stale pre-work sweep) fired once after editing scope files; fixed
with `frob ticket sweep T-0197` before the final check, per the CLI's own
suggested remedy.

REL001 disclosure: `DupConfig`/`DupStats` gained new public fields
(`prefilter_enabled`, `prefilter_size_ratio`, `prefilter_metric_ratio`,
`prefilter_vector_similarity`, `pairs_prefiltered`) -- an additive,
backward-compatible public-model change (new fields with defaults, no
existing field changed or removed). The release gate did not flag REL001
in this pass (`frob check --ticket T-0197` output has no REL001 line;
`.frob-release.json`'s stamped state was not updated/verified as part of
this ticket -- version-bump bookkeeping is the coordinator's land-time
step per the playbook, not scoped to this ticket).

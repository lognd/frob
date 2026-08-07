"""The smart-dup pipeline: fingerprint -> candidates -> verify -> report.

Implements docs/modules/dup.md's `find_clones` across the full rung ladder:

- R1 (exact token hash) and R2 (alpha-renamed token hash) are pure Python,
  always available -- they operate directly on `frob.lang`'s
  `RawSymbol.body_tokens`.
- R1.5 (exact repeated-region discovery via a generalized suffix array,
  `_region_groups`) needs `frob_core` AND is off by default even when R3+
  is enabled -- see `DupConfig.region_kernel_enabled` / `[dup].region_kernel`
  in frob.toml. R1/R2 hash whole symbol bodies, so a copy-pasted block
  sitting inside two otherwise-different symbols is invisible to them; R1.5
  closes that gap without waiting for R4's probabilistic winnowing.
- R3 (canonicalized subtree hash), R4 (winnowed fingerprints + candidate
  discovery + statement-alignment verification), and R5 (Weisfeiler-Lehman
  dataflow-graph hashing) all need the `frob_core` native extension. Per
  docs/modules/dup.md's no-silent-fallback rule there is no pure-Python
  reimplementation of R3+ to fall back on: `find_clones` treats the whole
  ladder as one call and returns `Err(DupError.CoreUnavailable)` up front
  when `frob_core` is not importable.
- R6 (`probe_equivalence`) is opt-in and orchestrated separately -- it is
  never called from `find_clones`/the DUP gate path, only from a caller
  that explicitly wants behavioral probing (docs/modules/dup.md: "opt-in --probe
  path").

**Deviations from docs/modules/dup.md** (recorded, not silently dropped):
- R2's error-channel and combined-vs-split guard normalization
  (`_normalize_error_channel`, T-0785; `_abstract_if_conditions` +
  `_collapse_duplicate_guard_chains`, T-0801/T-0800) both abstract away
  token content that would otherwise sink two structurally-identical
  functions below R4's `_R4_SIMILARITY_FLOOR` purely on error-signaling-
  idiom or guard-clause-shape grounds: `frob.tickets._leases
  ._git_common_dir` and `frob.gates._exclude_hazard._git_common_dir`
  (both thin `Result`/`Optional`-flavored wrappers over the single
  canonical `frob.gitio.git_common_dir`, T-0784) are the real pair this
  was written against -- they measure r4 similarity 0.647 (above the 0.6
  floor) with both normalizations in place; see
  `TestErrorChannelDupPairing`/`TestConditionalShapeDupPairing` in
  `tests/test_dup.py`. Condition tokens are abstracted uniformly (like
  R2's identifier renaming), not just for this one pair, so ANY two
  `if`-headers compare as the same shape regardless of what they
  guard -- a real over-fire risk if left unchecked; see
  `TestErrorChannelNormalizationDoesNotOverFire`'s negative control for why
  this stays safe (the REST of a body still has to match for a false pair
  to form).
- R2's alpha-renaming abstracts every identifier-shaped token uniformly
  (no scope/locals distinction), because `frob.lang.RawSymbol.body_tokens`
  is a flat leaf-token tuple with no node-type metadata attached -- unlike
  the legacy `frob.dup._legacy` scanner, which walked tree-sitter nodes
  directly. Good enough to catch pure rename clones; a future
  `frob.lang` token-kind channel would make it exact.
- R3 is computed by the frob_core kernel over the R2-normalized token
  stream. `frob_core::r3_canonicalize` (T-0447) further abstracts
  numeric/string-literal-shaped tokens to a shared placeholder and
  desugars `elif` to `else: if` before folding, so R3 now independently
  fires on literal-only and elif-vs-nested-if/else differences R2 misses
  -- see `tests/test_dup.py`. Commutative-operand ordering and real
  for/while loop-shape desugaring still need actual AST structure (not a
  token fold) and remain unimplemented (`frob:todo T-0001`), since
  `frob.lang` does not yet expose per-token node-type metadata.
- **R4 verification is now real tree edit distance.** `_apted_similarity_for_pair`
  calls `frob.lang.symbol_tree` to get actual node structure for both
  candidates and runs `frob_core._apted_similarity` (Zhang-Shasha over the
  real subtree, not a flat statement sequence) -- the REPORTED similarity
  on a `ClonePair` is this real metric. The statement-sequence Levenshtein
  (`_core._tree_edit_similarity`, still a real algorithm, just over a
  flatter unit) is kept as the near-miss floor check and the source of the
  region-span narrowing (`_region_span_for_alignment`) -- that alignment
  is still statement-index-based, not node-based, which is why it is kept
  separate from the reported similarity rather than replaced outright.
  Falls back to the statement-Levenshtein similarity when either side's
  subtree cannot be recovered (a parse failure, or a region whose span
  does not resolve to a single node).
- **Statement chunking is a keyword heuristic, not real AST statement
  boundaries** -- but only on the FALLBACK path now. `_split_statements`
  (cutting `body_tokens` at statement-starting keywords) still backs the
  R4 near-miss floor/alignment and the R5 fallback graph; the R5 primary
  path (`_real_dataflow_graph`) uses actual `block`-node children from
  `frob.lang.symbol_tree`, which are real AST statement boundaries, not a
  keyword guess. `frob:todo T-0001` follow-up: extend real statement
  boundaries to the R4 alignment/region-span path too.
- **R5's def-use/control-dependence graph is real when a `frob.lang`
  subtree is available, across every grammar `_BLOCK_LABELS` names, not
  Python only (T-0196).** `_real_dataflow_graph` finds the function's
  body-statement container (`_find_block`, matching `_BLOCK_LABELS`:
  python/rust `block`, typescript/tsx `statement_block`, c/cpp
  `compound_statement` -- each verified directly against that grammar's
  real parse tree, not assumed), labels identifiers "def"/"use" from
  actual assignment-node child position (`_ASSIGNMENT_LABELS` /
  `_DECLARATOR_LABELS`, not a "next token is `=`" guess), and adds a
  sequential control-flow edge between consecutive statements -- real
  execution order, which the old proxy had no notion of at all. Still not
  a full CFG (no branch-edge fan-out for `if`/`for`/`while`, no true
  reaching-definitions dataflow) and augmented assignment/tuple-unpacking/
  `for`-target binding still fold into "use" -- recorded as `frob:todo
  T-0001` follow-up. `_build_dataflow_graph` (the original co-occurrence
  proxy) is kept as the honest fallback for every region where no
  `_BLOCK_LABELS` node is found: non-function regions, parse failures, or
  a `frob.lang`-supported grammar (e.g. `strata`) whose body-container
  label is not yet in `_BLOCK_LABELS`. `docs/modules/dup.md` is not in
  T-0196's scope, so its per-language coverage disclosure is a filed
  follow-up (T-draft-75a6070b, mints a real id on land) rather than
  updated here -- the exact real-vs-fallback breakdown per grammar lives
  in `_BLOCK_LABELS`'/`_ASSIGNMENT_LABELS`'/`_DECLARATOR_LABELS`'
  docstrings above until that lands.
- **R7 (`_probe_smt_equivalence`) is the bounded-SMT rung** docs/modules/dup.md
  named as a research item, now real for its explicitly bounded subset:
  single-`return`, int/bool-annotated, straight-line functions built from
  `+ - * // %`, comparisons, `and/or/not`, and one `if`-expression --
  see `_smt_translate`'s accepted node set. Anything outside that subset
  is `Err(DupError.SmtUnsupported)`, never silently approximated. Opt-in
  and never called from `find_clones`/the gate path, same as R6. Requires
  the optional `z3-solver` dependency (`uv pip install frob[smt]`);
  degrades to `Err(DupError.SmtUnavailable)` without it.
- **R6's purity heuristic is conservative and token-based**, not a real
  effect analysis: a body is treated as pure only if it contains none of
  `_IMPURE_TOKENS` (IO, exec/eval, global/nonlocal, common stdlib
  side-effect modules). False negatives (rejecting an actually-pure
  function) are expected and safe; false positives (probing an impure
  function) are the failure mode this heuristic exists to avoid, so it
  errs toward refusal.
- R6 only probes Python callables loaded from the worktree by
  `importlib`; other `frob.lang` languages return `Err(DupError.NotPure)`
  (no cross-language FFI harness exists to call a Rust/TS/C function from
  Python).
- **R4 candidate pairs are pre-filtered before expensive verification**
  (T-0197, docs/modules/dup-sota-survey.md survey items 2/4/6): NiCad-style
  size-ratio (`_nicad_size_ratio_ok`), Oreo-style branch-count metric-ratio
  (`_oreo_metric_ratio_ok`), and a DECKARD-style characteristic-vector
  cosine similarity over R2-normalized token-shape categories
  (`_deckard_vector_ok`, `_characteristic_vector`) all run in
  `_r4_candidate_pair` before `_r4_verify_pair`'s statement-alignment/APTED
  path. These are PRUNE-ONLY: `tests/test_dup_prefilter.py` asserts
  enabling `cfg.prefilter_enabled` (the default) never changes the
  verified-clone set on the existing dup fixtures, only
  `DupStats.pairs_prefiltered`/`pairs_verified` counts. DECKARD's real
  characteristic vector is a per-subtree AST node-type histogram; this uses
  the R2-normalized LEXICAL token-shape stream instead (`frob.lang`
  currently exposes no per-token node-type metadata on `body_tokens`) --
  same class of approximation as R2/R3's identifier-shaped-token
  normalization above.
"""

from __future__ import annotations

from frob.dup._pipeline._callgraph import (
    _callee_name_map,
    _find_block,
    _is_symref,
    _real_dataflow_graph,
    touched_refs,
)
from frob.dup._pipeline._fingerprint import (
    _characteristic_vector,
    _cosine_similarity,
    _deckard_vector_ok,
    _nicad_size_ratio_ok,
    _oreo_metric_ratio_ok,
    _r4_candidate_pair,
    find_clones,
    find_helper_clones,
)
from frob.dup._pipeline._normalize import (
    _abstract_guard_exit_bodies,
    _abstract_if_conditions,
    _collapse_duplicate_guard_chains,
    _normalize_error_channel,
    _r1_hash,
)
from frob.dup._pipeline._probe import probe_equivalence
from frob.dup._pipeline._shared import _KEYWORDS, _FpState
from frob.dup._pipeline._smt import _probe_smt_equivalence

# Re-exported for tests/callers that reach into pipeline internals directly
# (pre-existing usage this split (T-1086) preserves unchanged -- zero caller
# edits, per the T-1072/T-1076 precedent).
__all__ = [
    "_FpState",
    "_KEYWORDS",
    "_abstract_guard_exit_bodies",
    "_abstract_if_conditions",
    "_callee_name_map",
    "_characteristic_vector",
    "_collapse_duplicate_guard_chains",
    "_cosine_similarity",
    "_deckard_vector_ok",
    "_find_block",
    "_is_symref",
    "_nicad_size_ratio_ok",
    "_normalize_error_channel",
    "_oreo_metric_ratio_ok",
    "_probe_smt_equivalence",
    "_r1_hash",
    "_r4_candidate_pair",
    "_real_dataflow_graph",
    "find_clones",
    "find_helper_clones",
    "probe_equivalence",
    "touched_refs",
]

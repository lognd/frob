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

import hashlib
import importlib.util
import re
import time
import warnings
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from typani import Err, Ok
from typani.result import Result

from frob.dup import _cache, _core
from frob.dup._models import (
    CloneMatchGroup,
    ClonePair,
    CloneRegion,
    CloneReport,
    DupConfig,
    DupError,
    DupStats,
    ProbeVerdict,
)
from frob.dup._template import build_group_template
from frob.gitio import Diff
from frob.graph._models import GraphSnapshot, SymbolKind
from frob.graph.callgraph import CallGraph, build_call_graph, is_symref
from frob.lang._common import _CANONICAL_VOCAB
from frob.logging import get_logger
from frob.process._lock import derived_state_write_lock

_log = get_logger(__name__)

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Python-specific pseudo-keywords `frob.lang._common._CANONICAL_VOCAB`
# does not carry (it pools only constructs shared/analogous across at
# least two of python/typescript/rust/c/cpp; these are python-only literal
# spellings/soft keywords with no cross-grammar counterpart to pool
# against): `with`/`as`/`is`/`global`/`nonlocal`/`assert`/`del`/`await`
# have no entry there, and `None`/`True`/`False`/`self`/`cls` are literal
# or convention-bound spellings, not grammar keywords, so they would never
# belong in a cross-grammar keyword-vocabulary table.
_PY_ONLY_KEYWORDS = frozenset(
    {
        "with",
        "as",
        "is",
        "global",
        "nonlocal",
        "assert",
        "del",
        "await",
        "None",
        "True",
        "False",
        "self",
        "cls",
    }
)

# T-0487: `_KEYWORDS` was python-only, so a Rust `let` (or any other
# non-python grammar keyword: `fn`, `impl`, `struct`, `match`, `switch`,
# `case`, ...) matched `_IDENT_RE` and was never excluded, mis-labeling it
# as an identifier and skewing R2's alpha-rename hash plus R5's def-use
# labeling (`_labeled_ids`/`_add_chunk_nodes`) for every non-python
# grammar. Reusing `frob.lang._common._CANONICAL_VOCAB` (the existing
# pooled keyword/punctuation-spelling table `_BLOCK_LABELS`/
# `_ASSIGNMENT_LABELS` already mirror this per-grammar-pooled-into-one-set
# pattern for) closes that gap without a second hand-maintained per-
# language keyword list (NO DUPLICATION) -- its keys already cover every
# real keyword spelling `_canonical_tokens` treats as non-identifier
# across all five grammars; punctuation/operator entries in that table
# (e.g. `"{"`, `"="`) never match `_IDENT_RE` so folding them in here is
# harmless.
_KEYWORDS = _PY_ONLY_KEYWORDS | frozenset(_CANONICAL_VOCAB)

# Statement-starting keywords for the heuristic chunker (module docstring's
# "Statement chunking" deviation note).
_STMT_STARTERS = frozenset(
    {
        "if",
        "elif",
        "else",
        "for",
        "while",
        "return",
        "assert",
        "raise",
        "pass",
        "break",
        "continue",
        "with",
        "try",
        "except",
        "finally",
        "yield",
        "global",
        "nonlocal",
        "del",
        "import",
        "from",
    }
)

# Tokens that make a body ineligible for R6 probing (module docstring's
# "R6's purity heuristic" deviation note). Substring-matched against every
# token so `os.system`, `sys.exit`, dotted-attribute IO all trip it even
# though `frob.lang` tokens are leaf-level (e.g. "os", ".", "system").
_IMPURE_TOKENS = frozenset(
    {
        "open",
        "print",
        "input",
        "exec",
        "eval",
        "compile",
        "__import__",
        "global",
        "nonlocal",
        "os",
        "sys",
        "subprocess",
        "socket",
        "requests",
        "urllib",
        "random",
        "time",
        "datetime",
        "environ",
        "write",
        "read",
        "remove",
        "unlink",
        "system",
        "popen",
        "getenv",
        "setattr",
        "delattr",
    }
)

# R4 winnowing k-gram/window sizes and the near-miss acceptance floor.
_R4_K = 5
_R4_W = 4
_R4_MIN_SHARED = 2
_R4_SIMILARITY_FLOOR = 0.6
_R4_APTED_VERDICT_METHOD = "r4apted"

# Branch-shaped keywords counted for the Oreo-style metric-ratio pre-filter
# (docs/modules/dup-sota-survey.md item 6, non-ML half): a cheap McCabe-style
# complexity proxy over the token stream -- `frob.lang.RawSymbol.body_tokens`
# carries no per-token AST-node metadata, so an exact cyclomatic count is not
# available here; counting branch-starting keywords is the same order of
# approximation the module already uses for `_STMT_STARTERS`.
_BRANCH_KEYWORDS = frozenset(
    {"if", "elif", "for", "while", "try", "except", "case", "catch"}
)

# R5 iteration count for the WL-kernel refinement and its match similarity
# (WL hashing is a boolean collide/not-collide signal, not a continuous
# metric, so an exact-hash match is reported at a fixed high similarity).
_R5_ITERATIONS = 2
_R5_SIMILARITY = 0.88

# R5 real-CFG per-grammar node vocabulary (T-0196): each supported
# `frob.lang` grammar names its function-body statement container and its
# assignment-shaped statements differently (tree-sitter node `type`, which
# `TreeNode.label` mirrors verbatim -- verified directly against each
# grammar's parse tree, not assumed). `_find_block` and `_statement_ids`
# match against these sets instead of a single hardcoded label, so the real
# def-use/control-flow path (`_real_dataflow_graph`) covers every grammar
# whose body/assignment shape is listed here, not just Python's. A symbol
# whose grammar is not listed (or whose subtree does not match any of these
# labels) falls through to `_build_dataflow_graph`, the honest co-occurrence
# proxy -- see docs/modules/dup.md's per-language R5 coverage table for the
# current disclosure.
_BLOCK_LABELS = frozenset(
    {
        "block",  # python, rust
        "statement_block",  # typescript/tsx
        "compound_statement",  # c, cpp
    }
)
_ASSIGNMENT_LABELS = frozenset(
    {
        "assignment",  # python
        "assignment_expression",  # c, cpp, typescript/tsx (re-assignment)
        "let_declaration",  # rust `let x = ...;` (has a direct `=` child)
    }
)
# Declaration statements that wrap the actual def/use pair one level down
# (a direct `=`-bearing child) instead of carrying it themselves --
# `_statement_ids` descends into the first matching child rather than
# treating the whole wrapper as one flat "use" clique.
_DECLARATOR_LABELS = frozenset(
    {
        "variable_declarator",  # typescript/tsx `let`/`const`/`var` binding
        "init_declarator",  # c, cpp `int x = ...;`
    }
)

# Cache "method" tags and a fixed corpus epoch (bumped only if the
# winnowing/WL parameters above ever change -- there is no generator
# dependency for R4/R5, unlike R6's fuzz-corpus epoch).
_R4_VERDICT_METHOD = "r4"
_R5_FP_RUNG = "r5"
_R4_FP_RUNG = "r4fp"
_CORPUS_EPOCH = 0


def _r1_hash(tokens: tuple[str, ...]) -> str:
    """R1: exact token hash (copy-paste clones)."""
    return "r1:" + str(hash(tokens))


# T-0785 (audit M3): the marker every recognized error-channel exit shape
# collapses to. Three real functions in this repo (`frob.tickets._leases
# .git_common_dir` returning `Result[Path, LeaseError]` and
# `frob.gates._exclude_hazard._git_common_dir` returning `Path | None`)
# implement the SAME git-common-dir resolution logic but slipped under
# DUP's similarity threshold purely because one signals failure with
# `Err(...)`/`Ok(...)` and the other with `None`/the bare value -- an
# error-channel-SHAPE difference, not a logic difference. `_r2_normalize`
# runs this first so R2+ (everything downstream of alpha-renaming: R2's own
# hash, R3, R4's fingerprints/prefilter vector, R5) compares error-signaling
# idioms as the same shape; R1 (exact-token copy-paste hash) intentionally
# does not call this, since R1 exists to catch literal-identical text.
_ERROR_EXIT_MARKER = "$err_exit"

# Statement-starting keywords that end a `raise ...` statement's token run
# when reached at bracket depth 0 -- reuses `_STMT_STARTERS` (the same
# heuristic-statement-boundary set `_split_statements` already relies on)
# rather than inventing a second one.
_OPEN_BRACKETS = frozenset({"(", "[", "{"})
_CLOSE_BRACKETS = frozenset({")", "]", "}"})


def _matching_close_paren(tokens: tuple[str, ...], open_idx: int) -> int:
    """Index of the `)` matching the `(` at `open_idx` in `tokens`, tracking
    bracket depth across all of `(`/`[`/`{` so a nested call/collection
    inside the argument list does not close the outer paren early. Returns
    `len(tokens)` (an unreachable index, no matching close found) if the
    stream ends first -- callers slice up to this index either way, so an
    unbalanced/truncated token run degrades to "consume the rest" rather
    than raising.
    """
    depth = 0
    for idx in range(open_idx, len(tokens)):
        tok = tokens[idx]
        if tok in _OPEN_BRACKETS:
            depth += 1
        elif tok in _CLOSE_BRACKETS:
            depth -= 1
            if depth == 0:
                return idx
    return len(tokens)


# frob:waive ARCH001 reason="one cursor-driven token-stream scan (i/out/tokens all mutated together per iteration): each of the four exit shapes (Err/Ok/None/raise) advances i by a different amount and appends to the same out list before falling through to the next iteration; splitting a branch into a helper would require returning (new_i, appended_tokens) back to the loop for every branch, adding indirection without separating an independent sub-concern from the shared cursor"  # noqa: E501
def _normalize_error_channel(tokens: tuple[str, ...]) -> tuple[str, ...]:
    """Canonicalize `Result`/`Optional`/`raise` error-exit shapes in `tokens`
    to one shared form before similarity comparison (T-0785, audit M3):
    `return Err(...)` and `return None` both collapse to
    `return $ERROR_EXIT_MARKER` (their payload tokens dropped -- only the
    exit SHAPE matters, not which error value/enum member is carried);
    `return Ok(<expr>)` unwraps to `return <expr>` (the happy-path payload,
    same as a plain `Optional`-style `return <expr>`); a `raise ...`
    statement (its argument run heuristically bounded by the next
    depth-0 `_STMT_STARTERS` token, the same statement-boundary heuristic
    `_split_statements` already uses) collapses to `return
    $ERROR_EXIT_MARKER` too, since raising is also an error-channel exit.
    Every other token passes through unchanged.
    """
    out: list[str] = []
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if (
            tok == "return"
            and i + 2 < n
            and tokens[i + 1] == "Err"
            and tokens[i + 2] == "("
        ):
            close = _matching_close_paren(tokens, i + 2)
            out.append("return")
            out.append(_ERROR_EXIT_MARKER)
            i = close + 1
            continue
        if (
            tok == "return"
            and i + 2 < n
            and tokens[i + 1] == "Ok"
            and tokens[i + 2] == "("
        ):
            close = _matching_close_paren(tokens, i + 2)
            out.append("return")
            out.extend(tokens[i + 3 : close])
            i = close + 1
            continue
        if tok == "return" and i + 1 < n and tokens[i + 1] == "None":
            out.append("return")
            out.append(_ERROR_EXIT_MARKER)
            i += 2
            continue
        if tok == "raise":
            j = i + 1
            depth = 0
            while j < n:
                t = tokens[j]
                if t in _OPEN_BRACKETS:
                    depth += 1
                elif t in _CLOSE_BRACKETS:
                    depth -= 1
                elif depth == 0 and t in _STMT_STARTERS:
                    break
                j += 1
            out.append("return")
            out.append(_ERROR_EXIT_MARKER)
            i = j
            continue
        out.append(tok)
        i += 1
    return tuple(out)


# T-0801/T-0800 (dup-cluster normalization axis 2, promoted from T-0785's
# own "second, genuinely independent dimension" callout): the marker every
# `if <condition>:` header collapses its condition tokens to, once the
# condition's own content stops mattering for similarity comparison (only
# the fact that SOME condition gates the following body does). Kept
# distinct from `_ERROR_EXIT_MARKER` so a stray `if` inside an
# already-collapsed error-exit body can never be confused with the exit
# marker itself.
_IF_CONDITION_MARKER = "$cond"


def _matching_condition_colon(tokens: tuple[str, ...], if_idx: int) -> int:
    """Index of the `:` that closes the `if` header starting at `if_idx`,
    tracking bracket depth (same approach as `_matching_close_paren`) so a
    dict/slice/lambda colon nested inside the condition's own brackets is
    not mistaken for the header's closing colon. Returns `len(tokens)`
    (unreachable) if no depth-0 colon is found before the stream ends.
    """
    depth = 0
    for idx in range(if_idx + 1, len(tokens)):
        tok = tokens[idx]
        if tok in _OPEN_BRACKETS:
            depth += 1
        elif tok in _CLOSE_BRACKETS:
            depth -= 1
        elif tok == ":" and depth == 0:
            return idx
    return len(tokens)


def _abstract_if_conditions(tokens: tuple[str, ...]) -> tuple[str, ...]:
    """Collapse every `if`/`elif <condition>:` header's condition tokens to
    one shared `$cond` placeholder (T-0801/T-0800, dup-cluster
    normalization axis 2): a single combined guard (`if A or B:`) and a
    chain of split guards covering the same cases (`if A: ...` / `if B:
    ...`) differ token-for-token only in HOW MANY conditions are spelled
    out and what they say -- not in what either shape does structurally
    once its own condition is abstracted away, the same reasoning
    `_normalize_error_channel` already applies to exit payloads. `elif` is
    abstracted the SAME way as a bare `if` (not left with its condition
    literal) -- `frob_core::r3_canonicalize` (T-0447) desugars `elif` to
    `else: if` downstream of this pass, at the R3 layer, carrying whatever
    condition tokens are still attached forward unchanged; leaving `elif`'s
    condition literal here while a manually-nested `if`'s condition gets
    abstracted would silently break that elif-vs-nested-if/else R3
    equivalence for any pair whose conditions also differ in spelling
    (`tests/test_dup.py::TestR3ElifDesugar` covers this).
    """
    out: list[str] = []
    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok in ("if", "elif"):
            colon = _matching_condition_colon(tokens, i)
            out.append(tok)
            out.append(_IF_CONDITION_MARKER)
            if colon < n:
                out.append(":")
                i = colon + 1
            else:
                i = colon
            continue
        out.append(tok)
        i += 1
    return tuple(out)


# The canonical body every guard clause whose SOLE effect is "gate, then
# exit the same normalized error-channel way" collapses to, once its own
# condition is already abstracted (T-0801/T-0800). A guard's intermediate
# side-effecting content (a log call with a branch-specific message, most
# often) is exactly the kind of detail `_normalize_error_channel` already
# treats as noise for the exit payload itself; a guard clause that logs
# something DIFFERENT per branch but otherwise only gates+exits is the
# same shape as one that logs nothing, so both fold to this one body.
_GUARD_EXIT_BODY: tuple[str, ...] = ("return", _ERROR_EXIT_MARKER)


def _abstract_guard_exit_bodies(tokens: tuple[str, ...]) -> tuple[str, ...]:
    """After `_abstract_if_conditions`, collapse the body of every `if
    $cond: <body>` guard whose body's NEAREST unconditional tail (before
    either the stream ends or another `if $cond:` header is reached) is a
    normalized error-exit (`return $ERROR_EXIT_MARKER`,
    `_normalize_error_channel` already ran) down to that bare exit --
    dropping whatever branch-specific side-effecting content (a log call,
    a message string) sits in front of it (T-0801/T-0800). The guard's own
    real extent is only knowable up to that exit (this flat token stream
    carries no indentation/block-boundary info to bound it more precisely,
    same limitation `_split_statements`'s module-docstring deviation note
    already discloses) -- scanning stops and resumes right after the exit
    marker, so whatever real statement follows the guard in the source
    (not part of the guard's own body) is left untouched and re-scanned
    normally. A guard that does more than gate+exit before either
    boundary (no `return $ERROR_EXIT_MARKER` found before the next `if` or
    the stream ends) is left exactly as it was: this only fires on the
    specific "log-then-exit" guard-clause idiom the real motivating pair
    (`frob.tickets._leases._git_common_dir` /
    `frob.gates._exclude_hazard._git_common_dir`) used to split across two
    separately-worded guards, one per failure branch.
    """
    marker = ("if", _IF_CONDITION_MARKER, ":")
    n = len(tokens)
    out: list[str] = []
    i = 0
    # frob:waive PERF003 reason="two-pointer token scan (i advances past each matched guard), O(n) total, not a cross join"  # noqa: E501
    while i < n:
        if tuple(tokens[i : i + 3]) == marker:
            j = i + 3
            exit_end: int | None = None
            while j < n:
                if tuple(tokens[j : j + 3]) == marker:
                    break
                if tokens[j] == "return" and tokens[j + 1 : j + 2] == (
                    _ERROR_EXIT_MARKER,
                ):
                    exit_end = j + 2
                    break
                j += 1
            out.extend(marker)
            if exit_end is not None:
                out.extend(_GUARD_EXIT_BODY)
                i = exit_end
            else:
                i = i + 3
            continue
        out.append(tokens[i])
        i += 1
    return tuple(out)


#: The exact token run a bare guard-then-exit clause reduces to after
#: `_abstract_if_conditions` + `_abstract_guard_exit_bodies` -- a FIXED
#: length/shape (unlike the general "if $cond: <body>" span, whose body can
#: be anything), so `_collapse_duplicate_guard_chains` can match it
#: literally instead of re-deriving a boundary heuristic a second time.
_GUARD_EXIT_BLOCK: tuple[str, ...] = (
    "if",
    _IF_CONDITION_MARKER,
    ":",
) + _GUARD_EXIT_BODY


def _collapse_duplicate_guard_chains(tokens: tuple[str, ...]) -> tuple[str, ...]:
    """After `_abstract_if_conditions`/`_abstract_guard_exit_bodies`, fold a
    run of ADJACENT bare guard-then-exit blocks (`_GUARD_EXIT_BLOCK`, exactly
    `if $cond: return $ERROR_EXIT_MARKER`) into a single instance
    (T-0801/T-0800): this is the other half of the combined-vs-split axis --
    a chain of N single-condition early-return guards that all exit the same
    normalized way now reduces to the same shape as one guard with a
    compound condition, since the compound condition's own tokens were
    already abstracted away and each guard's side-effecting body (if any)
    was already collapsed to the bare exit by `_abstract_guard_exit_bodies`.
    Only ever DROPS an exact repeat of the immediately preceding guard
    block -- a guard whose body was NOT reduced to the bare exit shape (it
    does more than gate+exit) never matches `_GUARD_EXIT_BLOCK` and is left
    untouched, same conservative posture as R2's identifier abstraction:
    false negatives (an unmerged near-duplicate) are the accepted failure
    mode, not false positives.
    """
    block_len = len(_GUARD_EXIT_BLOCK)
    n = len(tokens)
    out: list[str] = []
    i = 0
    prev_was_block = False
    while i < n:
        if tuple(tokens[i : i + block_len]) == _GUARD_EXIT_BLOCK:
            if not prev_was_block:
                out.extend(_GUARD_EXIT_BLOCK)
            prev_was_block = True
            i += block_len
            continue
        out.append(tokens[i])
        prev_was_block = False
        i += 1
    return tuple(out)


def _normalize_guard_shape(tokens: tuple[str, ...]) -> tuple[str, ...]:
    """The combined-vs-split guard axis's full pass (T-0801/T-0800): abstract
    every `if` header's condition (`_abstract_if_conditions`), collapse a
    guard-then-exit body down to the bare exit regardless of its branch-
    specific side-effecting content (`_abstract_guard_exit_bodies`), then
    fold adjacent now-identical guard blocks into one
    (`_collapse_duplicate_guard_chains`) -- one shared entry point since
    both call sites that need this axis (`_r2_normalize`'s R2+ hash/
    fingerprint path and `_r4_alignment`'s near-miss floor) must apply the
    same three-step pass, not independently re-derive it.
    """
    tokens = _abstract_if_conditions(tokens)
    tokens = _abstract_guard_exit_bodies(tokens)
    return _collapse_duplicate_guard_chains(tokens)


def _r2_normalize(tokens: tuple[str, ...]) -> tuple[str, ...]:
    """Alpha-rename every identifier-shaped token to a positional placeholder,
    after first canonicalizing error-channel exits (T-0785,
    `_normalize_error_channel`) and combined-vs-split guard shape
    (T-0801/T-0800, `_normalize_guard_shape`) so a `Result`'s
    `Err(...)`/`Ok(...)`, an `Optional`'s `None`, a `raise`, and a chain of
    split early-return guards vs. one combined guard all compare as the
    same shape rather than as unrelated token runs.
    """
    tokens = _normalize_error_channel(tokens)
    tokens = _normalize_guard_shape(tokens)
    mapping: dict[str, str] = {}
    normalized: list[str] = []
    for tok in tokens:
        if _IDENT_RE.match(tok) and tok not in _KEYWORDS:
            if tok not in mapping:
                mapping[tok] = f"_v{len(mapping)}"
            normalized.append(mapping[tok])
        else:
            normalized.append(tok)
    return tuple(normalized)


def _r2_hash(tokens: tuple[str, ...]) -> str:
    """R2: alpha-renamed token hash -- every identifier-shaped token abstracted."""
    return "r2:" + str(hash(_r2_normalize(tokens)))


def _digest(tokens: tuple[str, ...]) -> str:
    """Content-addressed digest of a symbol body (the dup cache's cache key)."""
    payload = "\x00".join(tokens).encode("utf-8", "surrogatepass")
    return hashlib.sha256(payload).hexdigest()


def _split_statements(tokens: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    """Heuristic statement chunker -- see the module docstring's deviation note."""
    if not tokens:
        return ()
    chunks: list[list[str]] = [[]]
    for tok in tokens:
        if tok in _STMT_STARTERS and chunks[-1]:
            chunks.append([])
        chunks[-1].append(tok)
    return tuple(tuple(c) for c in chunks if c)


def _statement_hashes(chunks: tuple[tuple[str, ...], ...]) -> tuple[int, ...]:
    """One stable int hash per statement chunk, for `_tree_edit_similarity`."""
    return tuple(hash(c) & 0xFFFFFFFFFFFFFFFF for c in chunks)


def _line_for_statement_index(span: tuple[int, int], idx: int, total: int) -> int:
    """Best-effort line number for statement `idx` of `total`, spread over `span`.

    No real line-per-statement mapping exists (the heuristic chunker has no
    source-position info), so this distributes statement indices evenly
    across the symbol's known line span -- a documented approximation, not
    an exact mapping.
    """
    lo, hi = span
    if total <= 1:
        return lo
    frac = idx / (total - 1)
    return lo + round(frac * (hi - lo))


def _region_span_for_alignment(
    span: tuple[int, int],
    total: int,
    matched_indices: tuple[int, ...],
) -> tuple[int, int]:
    """The contiguous line subrange covering `matched_indices` of `total` statements.

    Falls back to the whole `span` when there is nothing to narrow (region-
    subsection matching per docs/modules/dup.md: a subsection hit should report a
    tighter span than the whole symbol whenever the alignment does not
    cover every statement).
    """
    if not matched_indices or total <= 1:
        return span
    lo_idx, hi_idx = min(matched_indices), max(matched_indices)
    lo = _line_for_statement_index(span, lo_idx, total)
    hi = _line_for_statement_index(span, hi_idx, total)
    return (min(lo, hi), max(lo, hi))


# frob:doc docs/modules/dup.md#pipeline
def touched_refs(snapshot: GraphSnapshot, diff: Diff) -> frozenset[str]:
    """Symrefs in `snapshot` whose span overlaps a `diff` hunk (the "new side")."""
    touched: set[str] = set()
    hunks_by_file: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for hunk in diff.hunks:
        hunks_by_file[hunk.file].append(hunk.span)
    for symref, record in snapshot.symbols.items():
        spans = hunks_by_file.get(record.id.path)
        if not spans:
            continue
        lo, hi = record.span
        for h_lo, h_hi in spans:
            if lo <= h_hi and h_lo <= hi:
                touched.add(symref)
                break
    return frozenset(touched)


def _parsed_symbols_by_path(root: Path, path: str) -> dict[str, tuple[str, ...]]:
    """qualname -> body_tokens for every symbol `frob.lang` extracts from `path`."""
    from frob.lang import parse_file

    result = parse_file(root / path)
    if result.is_err:
        _log.debug("find_clones: %s failed to parse (%s)", path, result.err)
        return {}
    return {s.qualname: s.body_tokens for s in result.danger_ok.symbols}


def _package_paths(root: Path, path: str) -> tuple[str, ...]:
    """Every language-supported file sitting next to `path` (same directory),
    repo-root-relative POSIX, `path` itself included -- the file set
    `build_call_graph` resolves intra-package private-helper calls over."""
    from frob.lang import supported_extensions

    directory = (root / path).parent
    if not directory.is_dir():
        return (path,)
    exts = supported_extensions()
    found = [
        (directory / name).relative_to(root).as_posix()
        for name in sorted(directory.iterdir())
        if (directory / name).is_file() and (directory / name).suffix.lower() in exts
    ]
    return tuple(found) or (path,)


def _call_graph_for_path(state: _FpState, path: str) -> CallGraph:
    """The (cached) intra-package call graph for `path`'s directory."""
    directory = str(Path(path).parent)
    cached = state.callgraph_by_dir.get(directory)
    if cached is not None:
        return cached
    graph = build_call_graph(state.root, _package_paths(state.root, path))
    state.callgraph_by_dir[directory] = graph
    return graph


def _caller_counts(state: _FpState, path: str, graph: CallGraph) -> dict[str, int]:
    """`{callee_symref: number-of-distinct-callers}` for `graph`, cached per
    directory (T-0288 shared-helper false-positive fix). A callee reached by
    more than one caller is CODE REUSE, not duplication: two unrelated
    functions calling the same private helper must not have that helper's
    body inflate their similarity. See `_substitute_calls`, which refuses to
    inline any callee with a count > 1 here."""
    directory = str(Path(path).parent)
    cached = state.caller_counts_by_dir.get(directory)
    if cached is not None:
        return cached
    counts: dict[str, int] = defaultdict(int)
    for callees in graph.calls.values():
        for callee_symref in set(callees):
            counts[callee_symref] += 1
    state.caller_counts_by_dir[directory] = counts
    return counts


# frob:ticket T-0814
def _is_symref(entry: str) -> bool:
    """True if `entry` looks like a real `path::qualname` call-graph node
    (a `CallGraph.calls` entry), false for a non-symref sentinel such as
    `frob.graph.callgraph.UNRESOLVED_CALLEE` -- every raw `graph.calls`
    consumer here must check this before `split("::", 1)`, which
    IndexErrors/ValueErrors on a bare sentinel with no `::` (T-0814). Thin
    wrapper over `frob.graph.callgraph.is_symref` (extracted T-0861)."""
    return is_symref(entry)


def _callee_name_map(graph: CallGraph, caller_symref: str) -> dict[str, str]:
    """`{short_call_name: callee_symref}` for one caller's recorded PRIVATE
    callees (see `build_call_graph`). Skips any non-symref sentinel entry
    (e.g. `UNRESOLVED_CALLEE`) -- it names no real callee to inline or
    splice (T-0814); downstream consumers (`_splice_call_site`,
    `_callee_tokens`) only ever see values pulled from this map, so
    filtering here protects them too."""
    result: dict[str, str] = {}
    for callee_symref in graph.calls.get(caller_symref, ()):
        if not _is_symref(callee_symref):
            continue
        short = callee_symref.split("::", 1)[1].rsplit(".", 1)[-1]
        result[short] = callee_symref
    return result


def _callee_tokens(state: _FpState, callee_symref: str) -> tuple[str, ...] | None:
    """`callee_symref`'s body tokens, parsing (and caching) its file on first use."""
    callee_path, callee_qualname = callee_symref.split("::", 1)
    if callee_path not in state.tokens_by_path:
        state.tokens_by_path[callee_path] = _parsed_symbols_by_path(
            state.root, callee_path
        )
    return state.tokens_by_path[callee_path].get(callee_qualname)


# NOTE (T-0288 reviewer reconcile, re: T-0290 reuse): `_substitute_calls`
# bounds its walk the same shape as `frob.graph.callgraph.closure` (depth
# cap, node budget, cycle guard via `visited`), but cannot delegate to
# `closure` directly -- `closure` returns a flat, already-decided BFS order
# of symrefs, whereas this function does interleaved TOKEN splicing:
# which callee to expand next depends on where its call-span sits inside
# the *already-substituted* token stream of its caller, and each splice
# consumes shared `budget` before the next call site is even scanned. That
# requires re-walking token-by-token, not just following a precomputed
# node list. Reusing `closure`'s bounds isn't cheap without changing its
# return shape, so the bounding constants (depth/nodes) are intentionally
# kept independent here; left as a note rather than a forced reuse.
def _substitute_calls(
    state: _FpState,
    path: str,
    caller_symref: str,
    tokens: list[str],
    visited: frozenset[str],
    budget: list[int],
    depth: int,
) -> list[str]:
    """IN-PLACE call-splicing: replace each resolved `name(...)` call span with
    the callee's own (recursively substituted) body tokens.

    Bounded: `depth >= inline_max_depth` or `budget[0] <= 0` stops
    substituting further and returns `tokens` unchanged past that point --
    the documented "fall back to the un-inlined body past the cap"
    behavior. Cycle-guarded via `visited` (a symref already on the current
    call chain is left as an un-substituted call, never re-entered).
    Public callees never appear in `graph.calls` at all (see
    `build_call_graph`), so this walk stops at the public-API boundary
    automatically -- no separate check needed here.

    SHARED-HELPER GUARD (T-0288 false-positive fix): a callee reached by
    more than one caller anywhere in `graph` (`_caller_counts`) is left as
    an opaque, un-substituted call on every side, never inlined. Sharing a
    helper is normal code reuse, not duplication -- inlining it into two
    unrelated callers would make the *shared helper's* body dominate their
    similarity instead of their own (distinct) logic. Only a private
    helper with exactly one caller gets inlined, which is exactly the case
    that matters for split-duplication detection: two differently-named,
    each-singly-called helpers with near-identical bodies still get
    expanded and compared.
    """
    if depth >= state.cfg.inline_max_depth or budget[0] <= 0:
        return tokens
    graph = _call_graph_for_path(state, path)
    name_map = _callee_name_map(graph, caller_symref)
    if not name_map:
        return tokens
    caller_counts = _caller_counts(state, path, graph)
    out: list[str] = []
    i = 0
    n = len(tokens)
    while i < n:
        # frob:invariant terminates reason="mutually recurses with _substitute_calls only through _splice_call_site, which increments depth and decrements budget[0] on every recursive descent; this call itself is a plain token scan, not a recursive step" measure="state.cfg.inline_max_depth - depth strictly decreases across the mutual-recursion chain, and budget[0] is checked >0 at each entry"  # noqa: E501
        spliced = _splice_call_site(
            state, tokens, i, name_map, visited, caller_counts, budget, depth
        )
        if spliced is not None:
            new_tokens, next_i = spliced
            out.extend(new_tokens)
            i = next_i
            continue
        out.append(tokens[i])
        i += 1
    return out


# frob:ticket T-0361
def _splice_call_site(
    state: _FpState,
    tokens: list[str],
    i: int,
    name_map: dict[str, str],
    visited: frozenset[str],
    caller_counts: dict[str, int],
    budget: list[int],
    depth: int,
) -> tuple[list[str], int] | None:
    """If `tokens[i]` starts a resolvable, inlinable, singly-called `name(...)`
    call site, scan to its matching close-paren and return the callee's
    recursively-substituted body tokens plus the token index just past the
    call; `None` if position `i` is not such a call site (left for the
    caller to append as an ordinary token). Split out of `_substitute_calls`'
    scan loop (T-0361)."""
    n = len(tokens)
    tok = tokens[i]
    if not (
        budget[0] > 0
        and i + 1 < n
        and tokens[i + 1] == "("
        and tok in name_map
        and name_map[tok] not in visited
        and caller_counts.get(name_map[tok], 0) <= 1
    ):
        return None
    callee_symref = name_map[tok]
    j = _matching_paren_end(tokens, i + 2)
    callee_tokens = _callee_tokens(state, callee_symref)
    if not callee_tokens:
        return None
    budget[0] -= 1
    callee_path = callee_symref.split("::", 1)[0]
    # frob:invariant terminates reason="_substitute_calls checks 'depth >= state.cfg.inline_max_depth or budget[0] <= 0' and returns immediately without recursing once either bound is hit; depth+1 is passed here and budget[0] was decremented above" measure="state.cfg.inline_max_depth - depth strictly decreases each recursive descent, bounded below by 0"  # noqa: E501
    substituted = _substitute_calls(
        state,
        callee_path,
        callee_symref,
        list(callee_tokens),
        visited | {callee_symref},
        budget,
        depth + 1,
    )
    return substituted, j


# frob:ticket T-0361
def _matching_paren_end(tokens: list[str], open_idx: int) -> int:
    """Token index just past the `)` matching the `(` already consumed at
    `open_idx - 1` (i.e. `open_idx` is the first token INSIDE the call's
    parens), scanning for nested parens; split out of `_splice_call_site`'s
    paren-depth scan (T-0361)."""
    n = len(tokens)
    paren_depth = 1
    j = open_idx
    while j < n and paren_depth > 0:
        if tokens[j] == "(":
            paren_depth += 1
        elif tokens[j] == ")":
            paren_depth -= 1
        j += 1
    return j


def _inline_private_calls(
    state: _FpState, symref: str, body_tokens: tuple[str, ...]
) -> tuple[str, ...]:
    """Splice bounded call-graph-closure PRIVATE-helper bodies into `body_tokens`.

    Triage-only: reported spans continue to point at the real helper
    definitions (`ClonePair.region` is built from `SymbolRecord.span`, never
    touched here) -- this only changes what gets hashed/compared. Falls
    back to `body_tokens` unchanged when inlining is disabled or the
    symbol has no private callees.
    """
    if not state.cfg.inline_calls:
        return body_tokens
    path = symref.split("::", 1)[0]
    budget = [state.cfg.inline_max_nodes]
    substituted = _substitute_calls(
        state, path, symref, list(body_tokens), frozenset({symref}), budget, depth=0
    )
    return tuple(substituted)


def _build_dataflow_graph(
    chunks: tuple[tuple[str, ...], ...],
) -> tuple[tuple[tuple[int, int], ...], tuple[str, ...]]:
    """R5 fallback: a co-occurrence adjacency + def/use labels over identifier
    tokens, used only when `_real_dataflow_graph` cannot recover real
    statement nodes (parse failure, non-function region). See the module
    docstring's "R5's def-use/control-dependence graph" deviation note --
    this token-proxy path is intentionally kept as the honest fallback, not
    silently passed off as the real thing.
    """
    nodes: list[str] = []  # label per node
    adjacency: list[tuple[int, int]] = []
    for chunk in chunks:
        _add_chunk_nodes(chunk, nodes, adjacency)
    return tuple(adjacency), tuple(nodes)


def _add_chunk_nodes(
    chunk: tuple[str, ...], nodes: list[str], adjacency: list[tuple[int, int]]
) -> None:
    """Append one statement chunk's identifier nodes (def/use) plus their
    pairwise co-occurrence edges to the running graph (R5 fallback proxy)."""
    chunk_node_ids: list[int] = []
    for i, tok in enumerate(chunk):
        if not (_IDENT_RE.match(tok) and tok not in _KEYWORDS):
            continue
        is_def = i + 1 < len(chunk) and chunk[i + 1] == "="
        nodes.append("def" if is_def else "use")
        chunk_node_ids.append(len(nodes) - 1)
    _add_clique_edges(chunk_node_ids, adjacency)


def _add_clique_edges(node_ids: list[int], adjacency: list[tuple[int, int]]) -> None:
    """Add every pairwise edge among `node_ids` (a co-occurrence clique)."""
    for a in range(len(node_ids)):
        for b in range(a + 1, len(node_ids)):
            adjacency.append((node_ids[a], node_ids[b]))


def _find_block(node: Any) -> Any | None:
    """Depth-first search for the first function-body statement container
    under `node`, across every `_BLOCK_LABELS` grammar (T-0196: was
    Python-only `"block"`; `frob.lang.symbol_tree` labels mirror each
    grammar's own tree-sitter node `type` verbatim, so python/rust both use
    `"block"` but typescript/tsx use `"statement_block"` and c/cpp use
    `"compound_statement"` -- verified against each grammar's real parse
    tree, not assumed)."""
    if node.label in _BLOCK_LABELS:
        return node
    for child in node.children:
        found = _find_block(child)
        if found is not None:
            return found
    return None


def _leaf_labels(node: Any) -> tuple[str, ...]:
    """Every leaf label under `node`, in order (a `TreeNode`'s own leaf tokens)."""
    if not node.children:
        return (node.label,)
    out: list[str] = []
    for child in node.children:
        out.extend(_leaf_labels(child))
    return tuple(out)


def _real_dataflow_graph(
    tree: Any,
) -> tuple[tuple[tuple[int, int], ...], tuple[str, ...]] | None:
    """R5 (real): a def-use adjacency plus sequential control-flow edges
    built from `frob.lang`'s actual statement nodes, not a token heuristic.
    Covers every grammar `_BLOCK_LABELS` names (python, rust, typescript/
    tsx, c, cpp -- T-0196), not Python only.

    See `_statement_sequence_graph` for the def-use/control-flow edge rules.
    Every direct child of the body-statement container (`_find_block`'s
    match) is a statement (`frob.lang.export_tree` mirrors each grammar's
    own tree-sitter shape as-is and does not wrap simple statements --
    `assignment`, bare `call`, etc. -- in an `expression_statement` node
    for python; T-0117 found the opposite assumption silently dropped every
    assignment statement, collapsing unrelated functions to identical
    single-node graphs and WL-hash-colliding them). No filtering by
    statement-type label is needed or correct here.

    Returns `None` (caller falls back to `_build_dataflow_graph`) when no
    `_BLOCK_LABELS` node is found under `tree` (a non-function region, a
    body with no direct statements, or a grammar not yet listed in
    `_BLOCK_LABELS`) -- an honest "can't build a real graph here," not a
    silent wrong answer.
    """
    block = _find_block(tree)
    if block is None or not block.children:
        return None
    statements = block.children
    if not statements:
        return None
    return _statement_sequence_graph(statements)


def _statement_sequence_graph(
    statements: list[Any],
) -> tuple[tuple[tuple[int, int], ...], tuple[str, ...]]:
    """Def-use cliques per statement plus sequencing edges between them, in order.

    Two edge kinds, both real (not proxied): **def-use** -- for an
    `assignment` node (bare or `expression_statement`-wrapped), targets
    (children before the `=` leaf) are labeled "def", the right-hand side
    "use", and every identifier within one statement is pairwise-connected;
    **control-flow** -- a sequencing edge from the last identifier node of
    statement *i* to the first identifier node of statement *i+1*, real
    adjacent-statement execution order the old co-occurrence proxy lacked.
    """
    labels: list[str] = []
    adjacency: list[tuple[int, int]] = []
    prev_last_idx: int | None = None

    for stmt in statements:
        stmt_ids = _statement_ids(stmt, labels)
        _add_clique_edges(stmt_ids, adjacency)
        if prev_last_idx is not None and stmt_ids:
            adjacency.append((prev_last_idx, stmt_ids[0]))
        if stmt_ids:
            prev_last_idx = stmt_ids[-1]

    return tuple(adjacency), tuple(labels)


def _labeled_ids(leaves: tuple[str, ...], role: str, labels: list[str]) -> list[int]:
    """Append `role` for each identifier leaf, returning the new node indices."""
    ids: list[int] = []
    for leaf in leaves:
        if _IDENT_RE.match(leaf) and leaf not in _KEYWORDS:
            labels.append(role)
            ids.append(len(labels) - 1)
    return ids


def _eq_index(children: list[Any]) -> int | None:
    """Index of the `=` leaf among an assignment node's children, or None."""
    for i, c in enumerate(children):
        if c.label == "=":
            return i
    return None


def _assignment_ids(assign: Any, labels: list[str]) -> list[int]:
    """Node ids for an assignment-shaped node (`_ASSIGNMENT_LABELS`):
    pre-`=` children are "def", the rest "use". Grammar-agnostic once the
    node has a direct `=` leaf child -- verified true for every label in
    `_ASSIGNMENT_LABELS`/`_DECLARATOR_LABELS` against each grammar's real
    parse tree."""
    eq_idx = _eq_index(assign.children)
    ids: list[int] = []
    for i, child in enumerate(assign.children):
        if child.label == "=":
            continue
        role = "def" if (eq_idx is not None and i < eq_idx) else "use"
        ids += _labeled_ids(_leaf_labels(child), role, labels)
    return ids


def _find_child_label(node: Any, wanted: frozenset[str]) -> Any | None:
    """First direct child of `node` whose label is in `wanted`, or None."""
    for child in node.children:
        if child.label in wanted:
            return child
    return None


def _statement_ids(stmt: Any, labels: list[str]) -> list[int]:
    """Node ids (with def/use labels appended to `labels`) for one statement.

    Three shapes, all real per-grammar node structure (T-0196, verified
    against each grammar's actual parse tree, not assumed):
    - `_ASSIGNMENT_LABELS` (python `assignment`, c/cpp/typescript
      `assignment_expression`, rust `let_declaration`) is handled whether
      it's the statement itself or wrapped one level under
      `expression_statement` (kept for robustness against other
      tree-sitter grammar builds that do wrap it).
    - `_DECLARATOR_LABELS` (typescript `variable_declarator` under a
      `lexical_declaration`/`variable_declaration` wrapper, c/cpp
      `init_declarator` under a `declaration` wrapper) carries the real
      `=` one level below the statement node -- descend into the first
      matching child rather than flattening the wrapper to one "use"
      clique.
    - Anything else (a bare expression statement, a control-flow header
      with no top-level assignment) falls back to "every identifier in
      this statement is a use" -- the same conservative default the
      original Python-only version used.
    """
    if stmt.label in _ASSIGNMENT_LABELS:
        return _assignment_ids(stmt, labels)
    if stmt.children and stmt.children[0].label in _ASSIGNMENT_LABELS:
        return _assignment_ids(stmt.children[0], labels)
    declarator = _find_child_label(stmt, _DECLARATOR_LABELS)
    if declarator is not None:
        return _assignment_ids(declarator, labels)
    return _labeled_ids(_leaf_labels(stmt), "use", labels)


def _core_symbol_tree(root: Path, record: Any) -> Any | None:
    """Best-effort `frob.lang.symbol_tree` for a snapshot symbol record, or
    `None` on any parse failure (callers fall back to the token proxy)."""
    from frob.lang import symbol_tree

    result = symbol_tree(root / record.id.path, record.span)
    return result.danger_ok if result.is_ok else None


def _apted_similarity_for_pair(
    root: Path, left_record: Any, right_record: Any
) -> float | None:
    """Real tree-edit-distance similarity for a candidate pair, or `None`
    if either side's subtree cannot be recovered (parse failure, or a
    region whose span no longer resolves to a single node -- callers fall
    back to the statement-Levenshtein similarity in that case)."""
    from frob.lang import symbol_tree
    from frob.lang._common import flatten_tree

    left_tree = symbol_tree(root / left_record.id.path, left_record.span)
    right_tree = symbol_tree(root / right_record.id.path, right_record.span)
    if left_tree.is_err or right_tree.is_err:
        _log.debug(
            "find_clones: apted subtree unavailable for %s or %s",
            left_record.id.path,
            right_record.id.path,
        )
        return None
    labels_a, parents_a = flatten_tree(left_tree.danger_ok)
    labels_b, parents_b = flatten_tree(right_tree.danger_ok)
    sim_result = _core._apted_similarity(
        tuple(labels_a), tuple(parents_a), tuple(labels_b), tuple(parents_b)
    )
    if sim_result.is_err:
        return None
    return sim_result.danger_ok


@dataclass
class _FpState:
    """Mutable accumulator threaded through the `find_clones` fingerprint and
    matching passes: per-rung buckets, the ref->tokens/digest/fp maps, and the
    running fingerprinted/cache-hit/pairs-verified counters."""

    root: Path
    cfg: DupConfig
    r1_buckets: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    r2_buckets: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    r3_buckets: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    r5_buckets: dict[int, list[str]] = field(default_factory=lambda: defaultdict(list))
    fingerprinted: int = 0
    cache_hits: int = 0
    pairs_verified: int = 0
    pairs_prefiltered: int = 0
    tokens_by_path: dict[str, dict[str, tuple[str, ...]]] = field(default_factory=dict)
    body_tokens_by_ref: dict[str, tuple[str, ...]] = field(default_factory=dict)
    digest_by_ref: dict[str, str] = field(default_factory=dict)
    fp_by_ref: dict[str, tuple[int, ...]] = field(default_factory=dict)
    callgraph_by_dir: dict[str, CallGraph] = field(default_factory=dict)
    caller_counts_by_dir: dict[str, dict[str, int]] = field(default_factory=dict)
    size_by_ref: dict[str, int] = field(default_factory=dict)
    metric_by_ref: dict[str, int] = field(default_factory=dict)
    vector_by_ref: dict[str, dict[str, int]] = field(default_factory=dict)


def _r3_fingerprint(
    state: _FpState, digest: str, normalized: tuple[str, ...]
) -> str | None:
    """R3 canonical hash for a normalized token stream, cache-backed. `None`
    when the frob_core kernel errors (caller skips the symbol's R4/R5)."""
    cached = _cache.get_fingerprint(state.root, digest, "r3")
    if cached is not None:
        state.cache_hits += 1
        return str(cached[0])
    result = _core._r3_canonical_hash(normalized)
    if result.is_err:
        return None
    _cache.put_fingerprint(state.root, digest, "r3", (result.danger_ok,))
    return result.danger_ok


def _r4_fingerprint(
    state: _FpState, symref: str, digest: str, normalized: tuple[str, ...]
) -> None:
    """Compute/cache the R4 winnowed fingerprint set for `symref`."""
    cached = _cache.get_fingerprint(state.root, digest, _R4_FP_RUNG)
    if cached is not None:
        state.cache_hits += 1
        state.fp_by_ref[symref] = cast("tuple[int, ...]", tuple(cached))
        return
    result = _core._winnow_fingerprints(normalized, _R4_K, _R4_W)
    if result.is_ok:
        state.fp_by_ref[symref] = result.danger_ok
        _cache.put_fingerprint(state.root, digest, _R4_FP_RUNG, result.danger_ok)


def _dataflow_graph(
    root: Path, record: Any, body_tokens: tuple[str, ...]
) -> tuple[tuple[tuple[int, int], ...], tuple[str, ...]]:
    """The R5 def-use/control graph for a symbol: the real statement-node
    graph when a subtree is available, else the token co-occurrence proxy."""
    body_tree = _core_symbol_tree(root, record)
    real = _real_dataflow_graph(body_tree) if body_tree is not None else None
    if real is not None:
        return real
    return _build_dataflow_graph(_split_statements(body_tokens))


def _r5_fingerprint(
    state: _FpState, digest: str, record: Any, body_tokens: tuple[str, ...]
) -> int | None:
    """R5 Weisfeiler-Lehman graph hash for a symbol, cache-backed. `None`
    when the frob_core kernel errors."""
    cached = _cache.get_fingerprint(state.root, digest, _R5_FP_RUNG)
    if cached is not None:
        state.cache_hits += 1
        return cast(int, cached[0])
    adjacency, labels = _dataflow_graph(state.root, record, body_tokens)
    result = _core._wl_hash(adjacency, labels, _R5_ITERATIONS)
    if result.is_err:
        return None
    _cache.put_fingerprint(state.root, digest, _R5_FP_RUNG, (result.danger_ok,))
    return result.danger_ok


def _body_tokens_for_symbol(state: _FpState, record: Any) -> tuple[str, ...] | None:
    """`record`'s body tokens (private-helper-inlined, T-0288), parsing/caching
    its file if not already loaded. `None` when the body is missing or the
    INLINED token count is under `cfg.min_tokens` -- inlining runs before the
    threshold check so a symbol whose logic was split into private helpers
    is measured by its real logic size, not the arch-forced call-site size.
    """
    path = record.id.path
    if path not in state.tokens_by_path:
        state.tokens_by_path[path] = _parsed_symbols_by_path(state.root, path)
    raw_tokens = state.tokens_by_path[path].get(record.id.qualname)
    if not raw_tokens:
        return None
    symref = f"{path}::{record.id.qualname}"
    body_tokens = _inline_private_calls(state, symref, raw_tokens)
    if len(body_tokens) < state.cfg.min_tokens:
        return None
    return body_tokens


def _fingerprint_symbol(state: _FpState, symref: str, record: Any) -> None:
    """Fingerprint one snapshot symbol into every rung bucket on `state`.

    Bucketing every symbol (not just touched ones) lets a touched symbol
    match a pre-existing, untouched one. Bodies below `cfg.min_tokens` are
    skipped. An R3 kernel error skips the symbol's remaining rungs.
    """
    body_tokens = _body_tokens_for_symbol(state, record)
    if body_tokens is None:
        return
    state.fingerprinted += 1
    state.body_tokens_by_ref[symref] = body_tokens
    digest = _digest(body_tokens)
    state.digest_by_ref[symref] = digest
    normalized = _r2_normalize(body_tokens)

    state.size_by_ref[symref] = len(body_tokens)
    state.metric_by_ref[symref] = sum(
        1 for tok in body_tokens if tok in _BRANCH_KEYWORDS
    )
    state.vector_by_ref[symref] = _characteristic_vector(normalized)

    state.r1_buckets[_r1_hash(body_tokens)].append(symref)
    state.r2_buckets[_r2_hash(body_tokens)].append(symref)

    # frob:ticket T-0974
    # R3-R5 are native-call-per-symbol and dominate cold-cache cost at
    # whole-snapshot scale (see DupConfig.native_rungs_enabled's docstring
    # for the measured budget-blowout this guards). R1/R2 above stay
    # unconditional -- cheap, pure-Python, and the reason `[dup].enforce`
    # can default on at all.
    if not state.cfg.native_rungs_enabled:
        return

    r3_hash = _r3_fingerprint(state, digest, normalized)
    if r3_hash is None:
        return
    state.r3_buckets["r3:" + r3_hash].append(symref)

    _r4_fingerprint(state, symref, digest, normalized)

    wl = _r5_fingerprint(state, digest, record, body_tokens)
    if wl is None:
        return
    state.r5_buckets[wl].append(symref)


def _pair(
    a: str,
    b: str,
    snapshot: GraphSnapshot,
    similarity: float,
    rung: str,
    alignment: tuple[tuple[int, int], ...] = (),
) -> ClonePair:
    """A `ClonePair` for refs `a`/`b` using each side's whole symbol span."""
    return ClonePair(
        left=CloneRegion(ref=a, span=snapshot.symbols[a].span),
        right=CloneRegion(ref=b, span=snapshot.symbols[b].span),
        similarity=similarity,
        rung=rung,
        alignment=alignment,
    )


def _bucket_pairs(
    members: list[str],
    touched: frozenset[str] | None,
    seen_pairs: set[frozenset[str]],
) -> Iterator[tuple[str, str]]:
    """Unordered new ref pairs in one bucket: skipping untouched-only pairs
    (when `touched` is set) and any pair already reported by an earlier rung."""
    if len(members) < 2:
        return
    for i in range(len(members)):
        for j in range(i + 1, len(members)):
            a, b = members[i], members[j]
            if touched is not None and a not in touched and b not in touched:
                continue
            if frozenset((a, b)) in seen_pairs:
                continue
            yield a, b


def _hash_rung_groups(
    state: _FpState,
    snapshot: GraphSnapshot,
    touched: frozenset[str] | None,
    seen_pairs: set[frozenset[str]],
) -> list[tuple[ClonePair, ...]]:
    """R1/R2/R3 exact-hash-collision clone groups."""
    groups: list[tuple[ClonePair, ...]] = []
    for name, buckets, similarity, rung in (
        ("r1", state.r1_buckets, 1.0, "r1"),
        ("r2", state.r2_buckets, 0.95, "r2"),
        ("r3", state.r3_buckets, 0.9, "r3"),
    ):
        for members in buckets.values():
            group = [
                _pair(a, b, snapshot, similarity, rung)
                for a, b in _consume_pairs(
                    _bucket_pairs(members, touched, seen_pairs), seen_pairs, state
                )
            ]
            if group:
                groups.append(tuple(group))
        _log.debug("find_clones: rung=%s buckets=%d", name, len(buckets))
    return groups


def _consume_pairs(
    pairs: Iterator[tuple[str, str]],
    seen_pairs: set[frozenset[str]],
    state: _FpState,
) -> Iterator[tuple[str, str]]:
    """Mark each yielded pair seen and count it verified as it is consumed."""
    for a, b in pairs:
        seen_pairs.add(frozenset((a, b)))
        state.pairs_verified += 1
        yield a, b


def _r4_alignment(
    state: _FpState, a: str, b: str, d1: str, d2: str
) -> tuple[float, tuple[tuple[int, int], ...]] | None:
    """The statement-Levenshtein similarity + alignment for an R4 candidate
    pair, cache-backed. `None` when the frob_core kernel errors."""
    cached = _cache.get_verdict(state.root, d1, d2, _R4_VERDICT_METHOD, _CORPUS_EPOCH)
    if cached is not None:
        state.cache_hits += 1
        raw = cast("list[list[int]]", cached[1])
        return cast(float, cached[0]), tuple((p[0], p[1]) for p in raw)
    # T-0785: channel-normalize (but do NOT alpha-rename -- real identifier
    # text still has to line up exactly for this near-miss floor's raw
    # per-statement hash match) before splitting into statements, so an
    # `Err(...)`/`None`/`raise` exit shape difference alone does not sink a
    # pair's near-miss floor the way the motivating git-common-dir pair did
    # (audit M3). `state.body_tokens_by_ref` itself stays untouched (R1's
    # exact-hash and the cache-key digest both intentionally still see the
    # literal, un-normalized text).
    # T-0801/T-0800: also fold in the combined-vs-split guard axis
    # (`_normalize_guard_shape`) here, not just in `_r2_normalize` -- this
    # near-miss floor is the actual gate the real git-common-dir pair was
    # sinking under (0.444, below `_R4_SIMILARITY_FLOOR`) even after
    # T-0785's error-channel axis alone; identifiers still stay literal,
    # same posture as the error-channel normalization above.
    a_hashes = _statement_hashes(
        _split_statements(
            _normalize_guard_shape(
                _normalize_error_channel(state.body_tokens_by_ref[a])
            )
        )
    )
    b_hashes = _statement_hashes(
        _split_statements(
            _normalize_guard_shape(
                _normalize_error_channel(state.body_tokens_by_ref[b])
            )
        )
    )
    result = _core._tree_edit_similarity(a_hashes, b_hashes)
    if result.is_err:
        return None
    sim, alignment_pairs = result.danger_ok
    _cache.put_verdict(
        state.root,
        d1,
        d2,
        _R4_VERDICT_METHOD,
        _CORPUS_EPOCH,
        (sim, alignment_pairs),
        state.cfg.cache_entries,
    )
    return sim, alignment_pairs


def _r4_spans(
    state: _FpState,
    a: str,
    b: str,
    snapshot: GraphSnapshot,
    alignment_pairs: tuple[tuple[int, int], ...],
) -> tuple[tuple[int, int], tuple[int, int]]:
    """The narrowed left/right region spans for an R4 match's alignment."""
    a_chunks = _split_statements(state.body_tokens_by_ref[a])
    b_chunks = _split_statements(state.body_tokens_by_ref[b])
    a_idx = tuple(p[0] for p in alignment_pairs)
    b_idx = tuple(p[1] for p in alignment_pairs)
    left = _region_span_for_alignment(snapshot.symbols[a].span, len(a_chunks), a_idx)
    right = _region_span_for_alignment(snapshot.symbols[b].span, len(b_chunks), b_idx)
    return left, right


def _r4_verify_pair(
    state: _FpState,
    a: str,
    b: str,
    snapshot: GraphSnapshot,
    seen_pairs: set[frozenset[str]],
) -> ClonePair | None:
    """Verify one R4 candidate pair, counting it and reporting a `ClonePair`
    when it clears the near-miss floor (else `None`)."""
    d1, d2 = state.digest_by_ref[a], state.digest_by_ref[b]
    verdict = _r4_alignment(state, a, b, d1, d2)
    if verdict is None:
        return None
    sim, alignment_pairs = verdict
    state.pairs_verified += 1
    seen_pairs.add(frozenset((a, b)))
    if sim < _R4_SIMILARITY_FLOOR:
        return None
    left_span, right_span = _r4_spans(state, a, b, snapshot, alignment_pairs)
    reported_sim = _r4_reported_sim(state, a, b, snapshot, d1, d2, sim)
    return ClonePair(
        left=CloneRegion(ref=a, span=left_span),
        right=CloneRegion(ref=b, span=right_span),
        similarity=reported_sim,
        rung="r4",
        alignment=alignment_pairs,
    )


def _r4_reported_sim(
    state: _FpState,
    a: str,
    b: str,
    snapshot: GraphSnapshot,
    d1: str,
    d2: str,
    fallback: float,
) -> float:
    """Reported R4 similarity: cached/real APTED, else `fallback`."""
    cached = _cache.get_verdict(
        state.root, d1, d2, _R4_APTED_VERDICT_METHOD, _CORPUS_EPOCH
    )
    if cached is not None:
        state.cache_hits += 1
        return cast(float, cached[0])
    apted_sim = _apted_similarity_for_pair(
        state.root, snapshot.symbols[a], snapshot.symbols[b]
    )
    if apted_sim is not None:
        _cache.put_verdict(
            state.root,
            d1,
            d2,
            _R4_APTED_VERDICT_METHOD,
            _CORPUS_EPOCH,
            (apted_sim, ()),
            state.cfg.cache_entries,
        )
        return apted_sim
    return fallback


def _r4_groups(
    state: _FpState,
    snapshot: GraphSnapshot,
    touched: frozenset[str] | None,
    seen_pairs: set[frozenset[str]],
) -> list[tuple[ClonePair, ...]]:
    """R4 near-miss clone groups: winnow-fingerprint candidates verified by
    statement alignment, then refined by real tree-edit distance."""
    r4_refs = list(state.fp_by_ref)
    if len(r4_refs) < 2:
        return []
    sets = tuple(state.fp_by_ref[r] for r in r4_refs)
    candidates_result = _core._candidate_pairs(sets, _R4_MIN_SHARED)
    if candidates_result.is_err:
        _log.debug("find_clones: r4 candidate discovery unavailable")
        return []
    r4_group: list[ClonePair] = []
    for i, j in candidates_result.danger_ok:
        pair = _r4_candidate_pair(state, r4_refs, i, j, snapshot, touched, seen_pairs)
        if pair is not None:
            r4_group.append(pair)
    return [tuple(r4_group)] if r4_group else []


def _characteristic_vector(normalized: tuple[str, ...]) -> dict[str, int]:
    """DECKARD-style characteristic vector (docs/modules/dup-sota-survey.md
    item 4, T-0197): a histogram over shape CATEGORIES of the R2-normalized
    token stream, one bucket per distinct keyword/punctuation token plus a
    single collapsed `"IDENT"` bucket for every alpha-renamed placeholder.

    Real DECKARD builds this histogram over per-subtree AST *node-type*
    labels; `frob.lang.RawSymbol.body_tokens` is a flat leaf-token tuple
    with no per-token node-type metadata, so this uses the R2-normalized
    LEXICAL shape as the cheap stand-in -- documented deviation, same
    posture as the module docstring's other "no `frob.lang` per-token
    metadata yet" notes. Collapsing all placeholders to one bucket keeps
    the vector identifier-count-position-independent (two trees renamed
    with a different NUMBER of distinct identifiers should still look
    similar), matching DECKARD's rename-invariance property.
    """
    histogram: dict[str, int] = defaultdict(int)
    for tok in normalized:
        bucket = "IDENT" if tok.startswith("_v") and tok[2:].isdigit() else tok
        histogram[bucket] += 1
    return dict(histogram)


def _cosine_similarity(vec_a: dict[str, int], vec_b: dict[str, int]) -> float:
    """Cosine similarity of two sparse count-histograms; `1.0` if both are empty."""
    if not vec_a and not vec_b:
        return 1.0
    if not vec_a or not vec_b:
        return 0.0
    keys = vec_a.keys() & vec_b.keys()
    dot = sum(vec_a[k] * vec_b[k] for k in keys)
    norm_a = sum(v * v for v in vec_a.values()) ** 0.5
    norm_b = sum(v * v for v in vec_b.values()) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _nicad_size_ratio_ok(state: _FpState, a: str, b: str) -> bool:
    """NiCad-style size-ratio pre-filter (docs/modules/dup-sota-survey.md
    item 2's one adoptable idea, T-0197): reject a candidate pair whose
    token-count ratio is wilder than `cfg.prefilter_size_ratio` -- two
    bodies of grossly different size are not a plausible Type-1/2/3 clone
    pair. `min/max` so the ratio is always in `(0, 1]`; missing sizes (a
    symbol not seen by `_fingerprint_symbol`, should not happen for an R4
    candidate) pass through rather than reject."""
    size_a, size_b = state.size_by_ref.get(a), state.size_by_ref.get(b)
    if not size_a or not size_b:
        return True
    ratio = min(size_a, size_b) / max(size_a, size_b)
    return ratio >= state.cfg.prefilter_size_ratio


def _oreo_metric_ratio_ok(state: _FpState, a: str, b: str) -> bool:
    """Oreo-style metric-ratio pre-filter (docs/modules/dup-sota-survey.md
    item 6, non-ML half, T-0197): reject a candidate pair whose branch-
    keyword count (a cheap McCabe-complexity proxy, `_BRANCH_KEYWORDS`)
    ratio is wilder than `cfg.prefilter_metric_ratio`. Add-one smoothed so
    two straight-line (zero-branch) bodies never spuriously divide-by-zero
    or get rejected outright -- only a real, large complexity gap prunes."""
    metric_a = state.metric_by_ref.get(a, 0) + 1
    metric_b = state.metric_by_ref.get(b, 0) + 1
    ratio = min(metric_a, metric_b) / max(metric_a, metric_b)
    return ratio >= state.cfg.prefilter_metric_ratio


def _deckard_vector_ok(state: _FpState, a: str, b: str) -> bool:
    """DECKARD characteristic-vector pre-filter (T-0197): reject a candidate
    pair whose `_characteristic_vector` cosine similarity is below
    `cfg.prefilter_vector_similarity` -- structurally dissimilar token-shape
    profiles are not a plausible clone pair. Missing vectors pass through
    rather than reject."""
    vec_a, vec_b = state.vector_by_ref.get(a), state.vector_by_ref.get(b)
    if vec_a is None or vec_b is None:
        return True
    return _cosine_similarity(vec_a, vec_b) >= state.cfg.prefilter_vector_similarity


def _passes_r4_prefilters(state: _FpState, a: str, b: str) -> bool:
    """All three R4 candidate pre-filters (T-0197), ANDed: NiCad size-ratio,
    Oreo metric-ratio, DECKARD characteristic-vector similarity. A pair must
    clear every filter to reach the expensive `_r4_verify_pair` alignment/
    APTED path -- these are PRUNE-ONLY (docs/modules/dup-sota-survey.md
    survey items 2/4/6): failing a filter skips verification, it never adds
    a clone report on its own. `cfg.prefilter_enabled=False` disables all
    three (the pre-T-0197 behavior, every candidate reaches verification)."""
    if not state.cfg.prefilter_enabled:
        return True
    return (
        _nicad_size_ratio_ok(state, a, b)
        and _oreo_metric_ratio_ok(state, a, b)
        and _deckard_vector_ok(state, a, b)
    )


def _r4_candidate_pair(
    state: _FpState,
    r4_refs: list[str],
    i: int,
    j: int,
    snapshot: GraphSnapshot,
    touched: frozenset[str] | None,
    seen_pairs: set[frozenset[str]],
) -> ClonePair | None:
    """One `_core._candidate_pairs` index pair, filtered and verified into a
    `ClonePair` (or `None`)."""
    if i == j:
        # T-0191: unlike _bucket_pairs' range(i+1, len(members)) (which
        # structurally cannot self-pair), frob_core._candidate_pairs can
        # hand back (i, i) when a symbol's own fingerprint set collides
        # with itself past _R4_MIN_SHARED -- observed for real on this
        # repo's dup cache module post-refactor. Skip rather than
        # report a symbol as its own clone.
        return None
    a, b = r4_refs[i], r4_refs[j]
    if a == b:
        return None
    if touched is not None and a not in touched and b not in touched:
        return None
    if frozenset((a, b)) in seen_pairs:
        return None
    if not _passes_r4_prefilters(state, a, b):
        state.pairs_prefiltered += 1
        return None
    return _r4_verify_pair(state, a, b, snapshot, seen_pairs)


def _region_line_span(
    span: tuple[int, int], start: int, length: int, total_tokens: int
) -> tuple[int, int]:
    """The approximate line subrange for a `[start, start+length)` token
    window inside a symbol spanning `span`, via the same proportional
    index/total interpolation `_line_for_statement_index` uses for
    statement indices -- there is no per-token line map (`body_tokens` is a
    flat leaf-token tuple), so this is a documented approximation, not an
    exact mapping."""
    lo = _line_for_statement_index(span, start, total_tokens)
    hi = _line_for_statement_index(
        span, min(start + length - 1, total_tokens - 1), total_tokens
    )
    return (min(lo, hi), max(lo, hi))


def _region_groups(
    state: _FpState,
    snapshot: GraphSnapshot,
    touched: frozenset[str] | None,
    seen_pairs: set[frozenset[str]],
    cfg: DupConfig,
) -> list[tuple[ClonePair, ...]]:
    """R1.5: exact repeated-region clone groups via the frob_core generalized
    suffix-array kernel over every fingerprinted symbol's R2-normalized
    token stream.

    Off by default (`cfg.region_kernel_enabled`, docs/modules/dup.md's
    `[dup].region_kernel` knob), an opt-in on top of `[dup].enforce` itself.
    Unlike R1/R2 (whole-body hashing), finds a copy-pasted sub-region living
    inside two otherwise-different symbol bodies.
    """
    if not cfg.region_kernel_enabled:
        return []
    refs = list(state.body_tokens_by_ref)
    if len(refs) < 2:
        return []
    normalized_docs = tuple(_r2_normalize(state.body_tokens_by_ref[r]) for r in refs)
    result = _core._exact_regions(
        normalized_docs, cfg.region_min_tokens, cfg.region_run_cap
    )
    if result.is_err:
        _log.debug("find_clones: r1.5 exact-region kernel unavailable")
        return []
    hits, truncated = result.danger_ok
    if truncated:
        # T-0273: an equal-token run exceeded [dup].region_run_cap and its
        # pair emission was capped -- an honest signal, not a silent drop
        # (the T-0193-recall-bug lesson). Some region pairs inside that
        # oversized run were not reported.
        _log.warning(
            "find_clones: r1.5 exact-region kernel truncated pair emission "
            "for at least one equal-token run larger than "
            "[dup].region_run_cap=%d; some region pairs in that run were "
            "not reported",
            cfg.region_run_cap,
        )
    group: list[ClonePair] = [
        pair
        for pair in (
            _region_candidate_pair(
                state, snapshot, refs, normalized_docs, touched, seen_pairs, hit
            )
            for hit in hits
        )
        if pair is not None
    ]
    return [tuple(group)] if group else []


def _region_candidate_pair(
    state: _FpState,
    snapshot: GraphSnapshot,
    refs: list[str],
    normalized_docs: tuple[tuple[str, ...], ...],
    touched: frozenset[str] | None,
    seen_pairs: set[frozenset[str]],
    hit: tuple[int, int, int, int, int],
) -> ClonePair | None:
    """One `_core._exact_regions` hit `(da, oa, db, ob, length)`, filtered and
    turned into an r1.5 `ClonePair` (or `None`)."""
    da, oa, db, ob, length = hit
    a, b = refs[da], refs[db]
    if a == b:
        return None
    if touched is not None and a not in touched and b not in touched:
        return None
    if frozenset((a, b)) in seen_pairs:
        return None
    seen_pairs.add(frozenset((a, b)))
    state.pairs_verified += 1
    left_span = _region_line_span(
        snapshot.symbols[a].span, oa, length, len(normalized_docs[da])
    )
    right_span = _region_line_span(
        snapshot.symbols[b].span, ob, length, len(normalized_docs[db])
    )
    return ClonePair(
        left=CloneRegion(ref=a, span=left_span),
        right=CloneRegion(ref=b, span=right_span),
        similarity=1.0,
        rung="r1.5",
    )


def _r5_groups(
    state: _FpState,
    snapshot: GraphSnapshot,
    touched: frozenset[str] | None,
    seen_pairs: set[frozenset[str]],
) -> list[tuple[ClonePair, ...]]:
    """R5 clone groups: WL-hash bucket collisions not found by an earlier rung."""
    r5_group = [
        _pair(a, b, snapshot, _R5_SIMILARITY, "r5")
        for members in state.r5_buckets.values()
        for a, b in _consume_pairs(
            _bucket_pairs(members, touched, seen_pairs), seen_pairs, state
        )
    ]
    return [tuple(r5_group)] if r5_group else []


# frob:doc docs/modules/dup.md#public-api
# frob:ticket T-0918
def find_clones(
    snapshot: GraphSnapshot, cfg: DupConfig, diff: Diff | None = None
) -> Result[CloneReport, DupError]:
    """Run the full R1-R5 rung ladder over `snapshot` (R6 is opt-in, separate).

    `diff` restricts the "new side" to touched symbols (the DUP001 gate
    path); `diff=None` scans the whole snapshot. Fingerprints and pairwise
    verdicts are read/written through `frob.dup._cache` (content-addressed
    by body digest), so re-runs over an unchanged body/pair skip recompute.

    T-0918: the fingerprint-cache rebuild below is wrapped in `frob.process.
    _lock.derived_state_write_lock`, which takes a real cross-process
    EXCLUSIVE `derived_state_lock` when called standalone but no-ops when
    this process already holds the lock in another thread (e.g. nested
    inside `frob check`'s SHARED hold) -- see that function's docstring
    for the full reentrancy contract and its accepted soundness trade-off.
    """
    if not _core.core_available():
        _log.warning(
            "find_clones: frob_core unavailable, refusing R3+ scan. %s",
            _core.INSTALL_HINT,
        )
        return Err(DupError.CoreUnavailable)

    root = Path(snapshot.root)
    with derived_state_write_lock(root):
        touched = touched_refs(snapshot, diff) if diff is not None else None
        state = _FpState(root=root, cfg=cfg)
        for symref, record in snapshot.symbols.items():
            _fingerprint_symbol(state, symref, record)

        groups = _all_rung_groups(state, snapshot, touched, cfg)
        return Ok(_clone_report(state, groups))


def _is_private_helper(record: Any) -> bool:
    """True for a FUNCTION/METHOD symbol whose short name is `_`-prefixed
    (private/module-local, not re-exported) -- the population `find_helper_clones`
    scans."""
    short = record.id.qualname.rsplit(".", 1)[-1]
    return (
        record.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD)
        and not record.public
        and short.startswith("_")
    )


# frob:doc docs/modules/dup.md#pipeline
def find_helper_clones(
    snapshot: GraphSnapshot, cfg: DupConfig
) -> Result[CloneReport, DupError]:
    """Dedicated dup pass over the PRIVATE-helper population (T-0288, pair (b)).

    Arch-forced over-splitting spawns families of near-identical tiny
    private helpers -- often below the whole-symbol `cfg.min_tokens`
    default, so `find_clones` alone would never compare them. This restricts
    the snapshot to private/module-local FUNCTION/METHOD symbols and reruns
    the same rung ladder with `cfg.helper_min_tokens` (a much lower floor)
    in place of `cfg.min_tokens`, so over-splitting is itself caught, not
    just the calls-inlined comparison `find_clones` now also does.
    """
    helper_symbols = {
        symref: record
        for symref, record in snapshot.symbols.items()
        if _is_private_helper(record)
    }
    helper_snapshot = snapshot.model_copy(update={"symbols": helper_symbols})
    helper_cfg = cfg.model_copy(update={"min_tokens": cfg.helper_min_tokens})
    return find_clones(helper_snapshot, helper_cfg)


def _clone_report(state: _FpState, groups: list[tuple[ClonePair, ...]]) -> CloneReport:
    """Assemble the final `CloneReport` (groups + run stats) and log the summary.

    Each group's `template` is best-effort: `build_group_template` never
    raises, returning `None` when reverse-templating is not possible for
    that group (docs/modules/dup.md's "Reverse-templating report" section)
    -- a missing template never blocks the report itself.
    """
    stats = DupStats(
        fingerprinted=state.fingerprinted,
        cache_hits=state.cache_hits,
        pairs_verified=state.pairs_verified,
        pairs_prefiltered=state.pairs_prefiltered,
    )
    clone_groups = tuple(
        CloneMatchGroup(pairs=group, template=build_group_template(state.root, group))
        for group in groups
    )
    _log.info(
        "find_clones: %d group(s), %d pair(s) verified, %d pair(s) prefiltered, "
        "%d symbol(s) fingerprinted, %d cache hit(s)",
        len(clone_groups),
        state.pairs_verified,
        state.pairs_prefiltered,
        state.fingerprinted,
        state.cache_hits,
    )
    return CloneReport(groups=clone_groups, stats=stats)


def _all_rung_groups(
    state: _FpState,
    snapshot: GraphSnapshot,
    touched: frozenset[str] | None,
    cfg: DupConfig,
) -> list[tuple[ClonePair, ...]]:
    """Every clone group across the R1-R5 ladder, in rung order (R1/R2/R3,
    R1.5, R4, R5)."""
    seen_pairs: set[frozenset[str]] = set()
    groups = _hash_rung_groups(state, snapshot, touched, seen_pairs)
    groups += _region_groups(state, snapshot, touched, seen_pairs, cfg)
    groups += _r4_groups(state, snapshot, touched, seen_pairs)
    groups += _r5_groups(state, snapshot, touched, seen_pairs)
    return groups


_builtin_generators_registered = False


def _ensure_builtin_generators() -> None:
    """Register plain-builtin Arbitrary strategies once (int/float/str/bool).

    `frob.fuzz.resolve` only derives generators for pydantic `BaseModel`
    subclasses or types with a declared/registered strategy -- it has no
    built-in fallback for `int`/`str`/etc. R6 probing overwhelmingly needs
    exactly those scalar types, so this registers them once, through the
    same public `frob.fuzz.register` mechanism the docs describe for
    "third-party types the caller cannot annotate" -- plain builtins are
    exactly that case for a probe harness that does not own the probed
    function's module.
    """
    global _builtin_generators_registered
    if _builtin_generators_registered:
        return
    from frob.fuzz._arbitrary import HYPOTHESIS_AVAILABLE, register

    if not HYPOTHESIS_AVAILABLE:
        return
    import hypothesis.strategies as st

    register(int, st.integers(min_value=-10_000, max_value=10_000))
    register(float, st.floats(allow_nan=False, allow_infinity=False, width=32))
    register(str, st.text(max_size=20))
    register(bool, st.booleans())
    _builtin_generators_registered = True


def _is_pure_heuristic(tokens: tuple[str, ...]) -> bool:
    """Conservative purity check -- see the module docstring's R6 deviation note."""
    return not any(tok in _IMPURE_TOKENS for tok in tokens)


def _load_python_callable(root: Path, path: str, qualname: str) -> Any | None:
    """Best-effort `importlib` load of a top-level or `Class.method` callable."""
    if not path.endswith(".py"):
        return None
    file_path = root / path
    try:
        module_name = f"_frob_dup_probe_{hash(path)}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - any import-time failure means "can't probe"
        _log.debug("probe_equivalence: failed to load %s: %s", path, exc)
        return None

    obj: Any = module
    for part in qualname.split("."):
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    return obj if callable(obj) else None


# frob:doc docs/modules/dup.md#public-api
def probe_equivalence(
    a: str, b: str, snapshot: GraphSnapshot, budget_s: float
) -> Result[ProbeVerdict, DupError]:
    """R6: observational-equivalence probing for effect-free candidate pairs.

    Refuses (`Err(NotPure)`/`Err(NoGenerator)`) unless both `a` and `b` pass
    the purity heuristic, load as importable callables, and `a`'s
    parameters all have a resolvable Arbitrary generator that `b` also
    accepts positionally -- see `_probe_setup`. Compares outputs for up to
    `budget_s` seconds; both sides are always called positionally
    (`_call_safe`), since a pair the prober cannot legitimately call that
    way must never fall through to a vacuous `equivalent=True` verdict.
    """
    setup = _probe_setup(a, b, snapshot)
    if setup.is_err:
        return Err(setup.danger_err)
    fn_a, fn_b, strategies = setup.danger_ok

    verdict = _run_probe_cases(fn_a, fn_b, strategies, budget_s)
    return Ok(_probe_verdict(a, b, verdict))


def _probe_verdict(
    a: str, b: str, verdict: tuple[bool, int, dict[str, str] | None]
) -> ProbeVerdict:
    """Log and package a `_run_probe_cases` result as the final `ProbeVerdict`."""
    equivalent, cases_run, counterexample = verdict
    _log.info(
        "probe_equivalence: %s vs %s -- equivalent=%s cases_run=%d",
        a,
        b,
        equivalent,
        cases_run,
    )
    return ProbeVerdict(
        left=a,
        right=b,
        equivalent=equivalent,
        cases_run=cases_run,
        counterexample=counterexample,
    )


def _probe_setup(
    a: str, b: str, snapshot: GraphSnapshot
) -> Result[tuple[Any, Any, dict[str, Any]], DupError]:
    """Resolve `a`/`b` to callables and `a`'s Arbitrary strategies, verifying
    `b` accepts the same positional arity -- everything `probe_equivalence`
    needs before it can actually run cases."""
    callables = _probe_callables(a, b, snapshot)
    if callables.is_err:
        return Err(callables.danger_err)
    fn_a, fn_b = callables.danger_ok

    strategies_r = _probe_strategies(fn_a)
    if strategies_r.is_err:
        return Err(strategies_r.danger_err)
    strategies = strategies_r.danger_ok

    if not _probe_arity_compatible(fn_b, len(strategies)):
        _log.info(
            "probe_equivalence: %s vs %s -- fn_b rejects %d positional arg(s)",
            a,
            b,
            len(strategies),
        )
        return Err(DupError.NoGenerator)
    return Ok((fn_a, fn_b, strategies))


def _probe_callables(
    a: str, b: str, snapshot: GraphSnapshot
) -> Result[tuple[Any, Any], DupError]:
    """Resolve `a`/`b` to importable pure Python callables, or `Err(NotPure)`
    when either is missing, effectful (purity heuristic), or unloadable."""
    root = Path(snapshot.root)
    a_rec = snapshot.symbols.get(a)
    b_rec = snapshot.symbols.get(b)
    if a_rec is None or b_rec is None:
        _log.debug("probe_equivalence: %s or %s not in snapshot", a, b)
        return Err(DupError.NotPure)

    a_tokens = _parsed_symbols_by_path(root, a_rec.id.path).get(a_rec.id.qualname)
    b_tokens = _parsed_symbols_by_path(root, b_rec.id.path).get(b_rec.id.qualname)
    if not a_tokens or not b_tokens:
        _log.debug("probe_equivalence: %s or %s has no body tokens", a, b)
        return Err(DupError.NotPure)
    if not (_is_pure_heuristic(a_tokens) and _is_pure_heuristic(b_tokens)):
        _log.info("probe_equivalence: %s vs %s -- purity heuristic refuses", a, b)
        return Err(DupError.NotPure)

    fn_a = _load_python_callable(root, a_rec.id.path, a_rec.id.qualname)
    fn_b = _load_python_callable(root, b_rec.id.path, b_rec.id.qualname)
    if fn_a is None or fn_b is None:
        _log.info("probe_equivalence: %s or %s could not be loaded as a callable", a, b)
        return Err(DupError.NotPure)
    return Ok((fn_a, fn_b))


def _probe_strategies(fn_a: Any) -> Result[dict[str, Any], DupError]:
    """Arbitrary generators for `fn_a`'s parameters, keyed by name.

    `Err(NoGenerator)` for var-args, keyword-only params, an unannotated
    parameter, or a type with no resolvable generator (see
    `_probe_param_strategy` for why KEYWORD_ONLY is rejected -- T-0041's
    vacuous-pass bug); `Err(NotPure)` if the signature is uninspectable.
    """
    import inspect

    from frob.fuzz._arbitrary import resolve

    _ensure_builtin_generators()

    try:
        sig = inspect.signature(fn_a)
    except (TypeError, ValueError):
        return Err(DupError.NotPure)

    strategies: dict[str, Any] = {}
    for name, param in sig.parameters.items():
        gen_result = _probe_param_strategy(param, resolve)
        if gen_result.is_err:
            return Err(gen_result.danger_err)
        strategies[name] = gen_result.danger_ok
    return Ok(strategies)


def _probe_param_strategy(param: Any, resolve: Any) -> Result[Any, DupError]:
    """One parameter's Arbitrary generator, or `Err(NoGenerator)` for
    var-args/keyword-only/unannotated/unresolvable -- see `_probe_strategies`.

    KEYWORD_ONLY is rejected for the same reason VAR_POSITIONAL/VAR_KEYWORD
    are: `_run_probe_cases` calls both `fn_a` and `fn_b` positionally
    (renamed clones have differently-named parameters, so keyword binding
    by `fn_a`'s names would call `fn_b` with the wrong names). A
    keyword-only parameter can never legitimately be supplied positionally,
    so probing it would always raise `TypeError` on the first case -- and
    because `_call_safe` maps matching exceptions to a comparable sentinel,
    two functions that are NOT equivalent but both reject positional
    calling would score `equivalent=True` on every case (the vacuous-pass
    bug this guard exists to close, T-0041 reviewer repro). A pair the
    prober cannot legitimately call this way must be an explicit refusal,
    never a verdict."""
    import inspect

    if param.kind in (
        inspect.Parameter.VAR_POSITIONAL,
        inspect.Parameter.VAR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    ):
        return Err(DupError.NoGenerator)
    annotation = param.annotation
    if annotation is inspect.Parameter.empty:
        return Err(DupError.NoGenerator)
    gen_result = resolve(annotation)
    if gen_result.is_err:
        return Err(DupError.NoGenerator)
    return Ok(gen_result.danger_ok)


def _probe_arity_compatible(fn_b: Any, n_positional: int) -> bool:
    """True if `fn_b` can be called with exactly `n_positional` positional
    arguments, checked via `Signature.bind` (never by calling `fn_b`).

    `_run_probe_cases` calls `fn_b(*args)` with `len(args) ==
    n_positional` (the count of `fn_a`'s probed parameters -- see
    `_probe_strategies`). If `fn_b` requires a different arity (extra
    required params, too few params, or a keyword-only param with no
    default that positional binding can't satisfy), the call always
    raises `TypeError`, which is not "equivalent" evidence -- it is an
    uncallable pair. Without this guard a differing-arity pair would
    silently degenerate into the same vacuous-pass failure mode
    `_probe_strategies`'s KEYWORD_ONLY rejection closes for `fn_a`: if
    `fn_a` also happens to raise on some input, `_call_safe`'s shared
    exception sentinel would count the mismatch as agreement. Checked
    with placeholder values via `bind`, so this never partially
    executes `fn_b`.
    """
    import inspect

    try:
        sig_b = inspect.signature(fn_b)
        sig_b.bind(*([None] * n_positional))
    except TypeError:
        return False
    except ValueError:
        return False
    return True


def _call_safe(fn: Any, args: tuple[Any, ...]) -> Any:
    """Call `fn(*args)` positionally, mapping any exception to a comparable
    sentinel so two callables that fail the same way compare equal.

    Positional, not keyword, because R6's whole purpose is comparing
    *renamed* clones -- `fn_b`'s parameters routinely have different names
    than `fn_a`'s (that is the rename), so binding by name would call
    `fn_b` with `fn_a`'s parameter names and raise a spurious TypeError on
    every renamed pair, making renamed clones always compare unequal.
    """
    try:
        return fn(*args)
    except Exception as exc:  # noqa: BLE001 - comparing failure modes, not raising
        return ("__frob_exc__", type(exc).__name__)


def _run_probe_cases(
    fn_a: Any, fn_b: Any, strategies: dict[str, Any], budget_s: float
) -> tuple[bool, int, dict[str, str] | None]:
    """Draw inputs and compare `fn_a`/`fn_b` outputs until they diverge, the
    case budget is hit, or `budget_s` elapses.

    Inputs are drawn once per case (keyed on `fn_a`'s parameter names, in
    declaration order) and passed to BOTH callables positionally in that
    same order -- see `_call_safe` for why keyword-binding would be wrong
    for renamed clones.
    """
    cases_run = 0
    equivalent = True
    counterexample: dict[str, str] | None = None
    start = time.monotonic()
    max_cases = 50
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        while (
            equivalent and cases_run < max_cases and time.monotonic() - start < budget_s
        ):
            cases_run += 1
            counterexample = _probe_one_case(fn_a, fn_b, strategies)
            if counterexample is not None:
                equivalent = False
    return equivalent, cases_run, counterexample


def _probe_one_case(
    fn_a: Any, fn_b: Any, strategies: dict[str, Any]
) -> dict[str, str] | None:
    """Draw one case from `strategies` and call both callables with it;
    `None` if they agree, else the counterexample dict."""
    kwargs = {name: strategy.example() for name, strategy in strategies.items()}
    args = tuple(kwargs.values())
    result_a = _call_safe(fn_a, args)
    result_b = _call_safe(fn_b, args)
    if result_a == result_b:
        return None
    return {
        **{k: repr(v) for k, v in kwargs.items()},
        "left_result": repr(result_a),
        "right_result": repr(result_b),
    }


# R7 (opt-in, bounded-SMT): the AST node types `_smt_translate` accepts.
# Deliberately tiny -- straight-line int/bool arithmetic and comparisons
# only, no loops/calls/attribute access. Anything outside this subset is
# Err(SmtUnsupported), never a silent "probably fine."
_SMT_BINOPS = {"Add", "Sub", "Mult", "FloorDiv", "Mod"}
_SMT_CMPOPS = {"Eq", "NotEq", "Lt", "LtE", "Gt", "GtE"}
_SMT_BOOLOPS = {"And", "Or"}


def _smt_translate(node: Any, z3: Any, env: dict[str, Any]) -> Any:
    """Recursively translate a bounded Python-`ast` expression subtree into
    a Z3 expression over `env` (name -> Z3 const). Raises `ValueError` for
    anything outside `_SMT_BINOPS`/`_SMT_CMPOPS`/`_SMT_BOOLOPS`/literals/
    names/`if`-expressions/`not`/unary-minus -- the caller converts that
    into `Err(SmtUnsupported)`, never silently drops the term.
    """
    import ast as _ast

    if isinstance(node, _ast.IfExp):
        # frob:invariant terminates reason="node.test/body/orelse are node's own AST fields, each a proper descendant node in the finite Python ast tree produced by ast.parse; _smt_translate_simple and its helpers (_smt_unaryop/_smt_binop/_smt_boolop/_smt_compare) mutually recurse the same way, only ever descending into a field of their argument" measure="node's ast subtree depth strictly decreases"  # noqa: E501
        return z3.If(
            _smt_translate(node.test, z3, env),
            _smt_translate(node.body, z3, env),
            _smt_translate(node.orelse, z3, env),
        )
    handled = _smt_translate_simple(node, z3, env)
    if handled is not _SMT_UNHANDLED:
        return handled
    raise ValueError(f"unsupported node {type(node).__name__}")


_SMT_UNHANDLED = object()


def _smt_translate_simple(node: Any, z3: Any, env: dict[str, Any]) -> Any:
    """The non-`IfExp` cases of `_smt_translate`: literals, names, unary/binary/bool
    ops, and comparisons. Returns the `_SMT_UNHANDLED` sentinel for anything else."""
    import ast as _ast

    if isinstance(node, _ast.Constant) and isinstance(node.value, bool):
        return z3.BoolVal(node.value)
    if isinstance(node, _ast.Constant) and isinstance(node.value, int):
        return z3.IntVal(node.value)
    if isinstance(node, _ast.Name):
        if node.id not in env:
            raise ValueError(f"unbound name {node.id!r}")
        return env[node.id]
    if isinstance(node, _ast.UnaryOp):
        return _smt_unaryop(node, z3, env)
    if isinstance(node, _ast.BinOp):
        return _smt_binop(node, z3, env)
    if isinstance(node, _ast.BoolOp):
        return _smt_boolop(node, z3, env)
    if (
        isinstance(node, _ast.Compare)
        and len(node.ops) == 1
        and len(node.comparators) == 1
    ):
        return _smt_compare(node, z3, env)
    return _SMT_UNHANDLED


def _smt_unaryop(node: Any, z3: Any, env: dict[str, Any]) -> Any:
    """Translate a unary `-`/`not` expression to Z3."""
    import ast as _ast

    operand = _smt_translate(node.operand, z3, env)
    if isinstance(node.op, _ast.USub):
        return -operand
    if isinstance(node.op, _ast.Not):
        return z3.Not(operand)
    raise ValueError(f"unsupported unary op {type(node.op).__name__}")


def _smt_binop(node: Any, z3: Any, env: dict[str, Any]) -> Any:
    """Translate a bounded arithmetic binary op (`+ - * // %`) to Z3."""
    op_name = type(node.op).__name__
    if op_name not in _SMT_BINOPS:
        raise ValueError(f"unsupported binop {op_name}")
    left = _smt_translate(node.left, z3, env)
    right = _smt_translate(node.right, z3, env)
    return {
        "Add": lambda: left + right,
        "Sub": lambda: left - right,
        "Mult": lambda: left * right,
        "FloorDiv": lambda: left / right,
        "Mod": lambda: left % right,
    }[op_name]()


def _smt_boolop(node: Any, z3: Any, env: dict[str, Any]) -> Any:
    """Translate an `and`/`or` expression to Z3."""
    op_name = type(node.op).__name__
    if op_name not in _SMT_BOOLOPS:
        raise ValueError(f"unsupported boolop {op_name}")
    values = [_smt_translate(v, z3, env) for v in node.values]
    return z3.And(*values) if op_name == "And" else z3.Or(*values)


def _smt_compare(node: Any, z3: Any, env: dict[str, Any]) -> Any:
    """Translate a single-operator comparison to Z3."""
    op_name = type(node.ops[0]).__name__
    if op_name not in _SMT_CMPOPS:
        raise ValueError(f"unsupported compare op {op_name}")
    left = _smt_translate(node.left, z3, env)
    right = _smt_translate(node.comparators[0], z3, env)
    return {
        "Eq": lambda: left == right,
        "NotEq": lambda: left != right,
        "Lt": lambda: left < right,
        "LtE": lambda: left <= right,
        "Gt": lambda: left > right,
        "GtE": lambda: left >= right,
    }[op_name]()


def _smt_function_expr(source: str, z3: Any) -> tuple[Any, list[Any]] | None:
    """Parse `source` (one `def f(...): return <expr>` function) into a Z3
    expression plus its ordered parameter consts, or `None` if it is not a
    single-return, int/bool-annotated, bounded-subset function."""
    import ast as _ast

    tree = _ast.parse(source)
    if len(tree.body) != 1 or not isinstance(tree.body[0], _ast.FunctionDef):
        return None
    fn = tree.body[0]
    if len(fn.body) != 1 or not isinstance(fn.body[0], _ast.Return):
        return None
    if fn.body[0].value is None:
        return None

    bound = _smt_bind_params(fn.args.args, z3)
    if bound is None:
        return None
    env, params = bound

    try:
        expr = _smt_translate(fn.body[0].value, z3, env)
    except ValueError as exc:
        _log.debug("_probe_smt_equivalence: unsupported subset (%s)", exc)
        return None
    return expr, params


def _smt_bind_params(
    args: list[Any], z3: Any
) -> tuple[dict[str, Any], list[Any]] | None:
    """Z3 int/bool consts for each `int`/`bool`-annotated argument, `None` if
    any argument's annotation is outside that bounded subset."""
    env: dict[str, Any] = {}
    params: list[Any] = []
    for arg in args:
        ann = getattr(arg.annotation, "id", None)
        if ann == "int":
            const = z3.Int(arg.arg)
        elif ann == "bool":
            const = z3.Bool(arg.arg)
        else:
            return None
        env[arg.arg] = const
        params.append(const)
    return env, params


# frob:doc docs/modules/dup.md#rung-r7
# frob:waive COV007 reason="docs/modules/dup.md's Rung R7 section individually \
# frob:describes this private helper by name (T-0529) -- a deliberate architecture \
# doc, not accidental drift onto a private helper"
def _probe_smt_equivalence(
    a: str, b: str, snapshot: GraphSnapshot
) -> Result[ProbeVerdict, DupError]:
    """R7 (opt-in, research-frontier per docs/modules/dup.md): bounded-SMT formal
    equivalence for tiny pure int/bool functions, via z3-solver.

    Degrades to `Err(SmtUnavailable)` when `z3-solver` is not installed
    (an optional dependency -- `uv pip install frob[smt]`), and to
    `Err(SmtUnsupported)` for anything outside the bounded subset
    `_smt_translate` accepts (straight-line int/bool arithmetic,
    comparisons, `and`/`or`/`not`, one `if`-expression return -- no loops,
    calls, or attribute access). Unlike R6's observational probing, an
    UNSAT result here is a formal proof of equivalence over the whole
    input domain, not evidence from sampled cases.
    """
    try:
        import z3  # ty: ignore[unresolved-import]  # optional dep, frob[smt]
    except ImportError:
        _log.warning("_probe_smt_equivalence: z3-solver not installed")
        return Err(DupError.SmtUnavailable)

    parsed = _smt_parse_pair(a, b, snapshot, z3)
    if parsed.is_err:
        return Err(parsed.danger_err)
    (expr_a, params_a), (expr_b, params_b) = parsed.danger_ok
    return _smt_solve(a, b, expr_a, params_a, expr_b, params_b, z3)


def _smt_parse_pair(
    a: str, b: str, snapshot: GraphSnapshot, z3: Any
) -> Result[tuple[tuple[Any, list[Any]], tuple[Any, list[Any]]], DupError]:
    """Load `a`/`b`, parse each into a bounded Z3 expression + param consts.

    `Err(NotPure)` if either symbol is missing; `Err(SmtUnsupported)` if
    either is unloadable, unreadable, outside the bounded subset, or the two
    differ in arity.
    """
    root = Path(snapshot.root)
    a_rec = snapshot.symbols.get(a)
    b_rec = snapshot.symbols.get(b)
    if a_rec is None or b_rec is None:
        return Err(DupError.NotPure)

    fn_a = _load_python_callable(root, a_rec.id.path, a_rec.id.qualname)
    fn_b = _load_python_callable(root, b_rec.id.path, b_rec.id.qualname)
    if fn_a is None or fn_b is None:
        return Err(DupError.SmtUnsupported)

    sources = _smt_dedented_sources(fn_a, fn_b)
    if sources is None:
        return Err(DupError.SmtUnsupported)
    src_a, src_b = sources

    parsed_a = _smt_function_expr(src_a, z3)
    parsed_b = _smt_function_expr(src_b, z3)
    if parsed_a is None or parsed_b is None:
        return Err(DupError.SmtUnsupported)
    if len(parsed_a[1]) != len(parsed_b[1]):
        return Err(DupError.SmtUnsupported)
    return Ok((parsed_a, parsed_b))


def _smt_dedented_sources(fn_a: Any, fn_b: Any) -> tuple[str, str] | None:
    """Dedented `inspect.getsource` for both callables, or `None` if either
    is unreadable (builtin, C extension, source file gone, ...)."""
    import inspect
    import textwrap

    try:
        return (
            textwrap.dedent(inspect.getsource(fn_a)),
            textwrap.dedent(inspect.getsource(fn_b)),
        )
    except (OSError, TypeError):
        return None


def _smt_solve(
    a: str,
    b: str,
    expr_a: Any,
    params_a: list[Any],
    expr_b: Any,
    params_b: list[Any],
    z3: Any,
) -> Result[ProbeVerdict, DupError]:
    """Check `expr_a != expr_b` for satisfiability: UNSAT proves equivalence,
    SAT yields a counterexample, UNKNOWN is `Err(SmtUnsupported)`."""
    # Share params_a's consts as both functions' free variables (b's own
    # params were already substituted in when translated with its own
    # env -- rebuild b's expr over a's consts by positional identity).
    solver = z3.Solver()
    subst = list(zip(params_b, params_a, strict=True))
    expr_b_over_a = z3.substitute(expr_b, *subst) if subst else expr_b
    solver.add(expr_a != expr_b_over_a)
    return _smt_verdict_for_check(a, b, solver, solver.check(), params_a, z3)


def _smt_verdict_for_check(
    a: str, b: str, solver: Any, verdict: Any, params_a: list[Any], z3: Any
) -> Result[ProbeVerdict, DupError]:
    """Turn a `solver.check()` result into the `_probe_smt_equivalence` verdict."""
    if verdict == z3.unsat:
        _log.info("_probe_smt_equivalence: %s vs %s -- proved equivalent", a, b)
        return Ok(ProbeVerdict(left=a, right=b, equivalent=True, cases_run=0))
    if verdict == z3.sat:
        model = solver.model()
        counterexample = {
            str(p): str(model.eval(p, model_completion=True)) for p in params_a
        }
        _log.info("_probe_smt_equivalence: %s vs %s -- counterexample found", a, b)
        return Ok(
            ProbeVerdict(
                left=a,
                right=b,
                equivalent=False,
                cases_run=1,
                counterexample=counterexample,
            )
        )
    _log.warning("_probe_smt_equivalence: %s vs %s -- solver returned unknown", a, b)
    return Err(DupError.SmtUnsupported)


__all__ = [
    "find_clones",
    "probe_equivalence",
    "_probe_smt_equivalence",
    "touched_refs",
]

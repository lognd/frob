"""Shared constants/types for `frob.dup._pipeline`'s split rung-ladder modules.

Split from the monolithic `dup/_pipeline.py` (T-1086, T-1076 remainder): the
module-level keyword/token tables and the `_FpState` fingerprint accumulator
are used across `_normalize.py`/`_callgraph.py`/`_fingerprint.py`/`_probe.py`,
so they live here as the one shared home rather than being duplicated per
submodule (NO DUPLICATION).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from frob.dup._models import DupConfig
from frob.graph.callgraph import CallGraph
from frob.lang._common import _CANONICAL_VOCAB
from frob.logging import get_logger

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

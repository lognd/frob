"""R1/R2 token normalization + statement chunking (split from `dup/_pipeline.py`,
T-1086).

R1 (exact token hash) and R2 (alpha-renamed token hash, with error-channel
and guard-shape canonicalization) plus the heuristic statement chunker the
R4 near-miss floor and R5 fallback graph both rely on -- see
docs/modules/dup.md#pipeline and the (former) module docstring's deviation
notes, now on `frob.dup._pipeline`'s `__init__.py`.
"""

from __future__ import annotations

import hashlib

from frob.dup._pipeline._shared import _IDENT_RE, _KEYWORDS, _STMT_STARTERS


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

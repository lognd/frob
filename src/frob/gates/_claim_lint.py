"""CLAIM001: a symbol docstring asserting never/always/idempotent-shaped
language with no `frob:invariant` binding anywhere in its own span is an
UNVERIFIED claim (docs/modules/gates.md#claim001-t-4116).

F-307 H3-4 (T-4109/T-4116): a docstring asserted "never raises" three
times in one file, bound to zero `frob:invariant` markers or property
tests -- exactly the gap `frob:invariant` plus the prove loop exist for,
but nothing flagged the UNBOUND CLAIM itself; a full invariant-coverage
sweep (`frob.gates._inv`'s INV001/INV002) only ever measures claims
someone already marked. This is NOT the same comparison as H3-9 (a
module docstring vs. that module's own code): this leaf's comparison is
symbol docstring text vs. THAT SAME symbol's own `frob:invariant`
binding -- a directive-PRESENCE check, never a code-behavior check.

DUPLICATION CHECK (per this ticket's own instruction to reuse or absorb
rather than duplicate): T-4186 ("lint: a never/always/idempotent
docstring or spec-row claim with no bound frob:invariant", scoped to
`src/frob/gates/_docblocks.py`) proposes the identical detection shape,
consolidating several independently-filed near-duplicates
(F-317/F-326/F-327/F-362/F-386). At the time this module was written,
T-4186 was still `queued` with no code landed and no worktree in
progress (`git log --grep T-4186` and `frob ticket show T-4186` both
checked before implementing, per this ticket's own instruction) -- so
there was nothing to absorb INTO yet. This module implements exactly
this ticket's OWN declared scope (`src/frob/gates/_claim_lint.py`, a
Python-only symbol-docstring check); T-4186's broader mandate (spec-row
clauses, decision-record rows, TypeScript) is a superset this module
does not attempt. Flagged in the Done report for the coordinator to
reconcile (one of these two tickets should absorb the other once both
have landed, rather than shipping two independently-maintained CLAIM001-
shaped detectors).

Detection: for every function/method/class `frob.lang.parse_file` extracts
from a tracked `.py` file, a WHOLE-WORD, case-insensitive match of
`_CLAIM_WORDS` (`never`/`always`/`idempotent`) against `RawSymbol.doc_text`
is a claim. The claim is unverified unless `frob.graph.dsl.parse_directives`
finds an `EdgeKind.INVARIANT` edge whose `src` is that exact symbol's own
symref (`f"{path}::{qualname}"`) -- the SAME symref format
`_enclosing_src` already builds for every other directive-binding gate in
this package (`_inv.py`, `_wire.py`), not a second convention. A `frob:waive
CLAIM001 reason="..."` edge targeting `CLAIM001` and bound to that same
symref suppresses the finding, exactly like every other `Violation` in
this codebase (T-0148's exact-symref-match precision, no file-wide
blanket fallback for a per-symbol rule)."""
# frob:ticket T-4116

from __future__ import annotations

import re
from pathlib import Path

from frob.excludes import iter_files
from frob.findings import Severity, Violation, WaiverRef
from frob.graph import Edge, EdgeKind
from frob.graph.dsl import parse_directives
from frob.lang import RawSymbol, SymbolKind, parse_file
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["claim_lint_gate"]

#: Whole-word, case-insensitive absolute-guarantee language this ticket's
#: own motivating report named -- kept to exactly these three (T-4186's
#: broader word list, e.g. "fails closed"/"guaranteed", is that ticket's
#: own, wider scope, not duplicated here).
_CLAIM_WORDS_RE = re.compile(r"\b(never|always|idempotent)\b", re.IGNORECASE)

#: `RawSymbol.kind`s this lint has an opinion about -- a docstring claim on
#: a function/method/class is a claim about BEHAVIOR; other kinds
#: (`CONST`/`TYPE`/module-level docstrings) are out of this leaf's scope.
_CLAIMABLE_KINDS = frozenset({SymbolKind.FUNCTION, SymbolKind.METHOD, SymbolKind.CLASS})


def _symref(path: str, qualname: str) -> str:
    """The `path::qualname` symref format every directive-binding gate in
    this package (`_inv.py`, `_wire.py`) already uses -- matches
    `frob.graph.dsl._enclosing_src`'s own construction exactly, so a
    directive placed the normal way is never missed by a second, subtly
    different convention."""
    return f"{path}::{qualname}"


def _invariant_bound_symrefs(edges: tuple[Edge, ...]) -> frozenset[str]:
    """Every symref carrying at least one `frob:invariant` directive
    anywhere in its own span, per this file's own directive edges."""
    return frozenset(e.src for e in edges if e.kind is EdgeKind.INVARIANT)


def _claim001_waivers_by_symref(edges: tuple[Edge, ...]) -> dict[str, WaiverRef]:
    """Every symref carrying a `frob:waive CLAIM001 reason="..."` directive,
    mapped to the `WaiverRef` it justifies -- the standard per-symbol
    escape hatch (T-0148's exact-symref precision, never a file-wide
    blanket match) for a claim genuinely covered by a differently-shaped
    test the directive convention cannot see."""
    return {
        e.src: WaiverRef(site=e.src, reason=e.attrs.get("reason", ""))
        for e in edges
        if e.kind is EdgeKind.WAIVE and e.target == "CLAIM001"
    }


# frob:ticket T-4116
# frob:enforces CHK-GATE-CLAIM001
def _claim_violation(
    rel: str,
    parsed_path: str,
    sym: RawSymbol,
    bound: frozenset[str],
    waivers: dict[str, WaiverRef],
) -> Violation | None:
    """CLAIM001 verdict for one candidate symbol: `None` when the claim is
    absent, bound to an invariant, or waived, else the `Violation` to
    report (split out of `claim_lint_gate` to keep that function under
    ARCH001's long-AND-complex threshold, per-symbol logic unchanged)."""
    if sym.kind not in _CLAIMABLE_KINDS:
        return None
    if not _CLAIM_WORDS_RE.search(sym.doc_text):
        return None
    # T-4116: match edges on `parsed_path` (whatever path `parse_file` was
    # invoked with, here the absolute file path), the SAME string
    # `frob.graph.dsl._enclosing_src` used to build every edge's own
    # `src` -- `rel` is a distinct, repo-relative spelling used only for
    # the reported `Violation.file`/display `symref`, never for edge
    # lookups.
    edge_symref = _symref(parsed_path, sym.qualname)
    symref = _symref(rel, sym.qualname)
    if edge_symref in bound:
        return None
    waiver = waivers.get(edge_symref)
    if waiver is not None:
        # T-4116: this standalone gate function is not yet wired into
        # `run_gates`'s shared `_match_waiver` filtering pipeline
        # (src/frob/gates/__init__.py is outside this ticket's scope, see
        # module docstring) -- honor the escape hatch directly here
        # rather than reporting a WARN this caller has no mechanism to
        # later suppress.
        return None
    return Violation(
        rule="CLAIM001",
        severity=Severity.WARN,
        file=rel,
        line=sym.span[0],
        message=(
            f"CLAIM001: {symref}'s docstring uses "
            f"never/always/idempotent-shaped language with no "
            f"frob:invariant directive bound to this symbol -- "
            f"an unverified claim (docs/modules/gates.md#claim001-t-4116); "
            f"add `frob:invariant INV-###` at the enforcing site, "
            f'or `frob:waive CLAIM001 reason="..."` if a '
            f"differently-shaped test already covers it"
        ),
        symref=symref,
    )


# frob:ticket T-4116
def _claim_violations_for_file(f: Path, root: Path) -> tuple[list[Violation], bool]:
    """CLAIM001 violations for one tracked `.py` file, and whether it was
    parseable (split out of `claim_lint_gate` to keep that function under
    ARCH001's long-AND-complex threshold, per-file logic unchanged)."""
    rel = f.relative_to(root).as_posix()
    parsed_result = parse_file(f, expect_heterogeneous=True)
    if parsed_result.is_err:
        return [], False
    parsed = parsed_result.danger_ok
    edges, _malformed = parse_directives(parsed)
    bound = _invariant_bound_symrefs(edges)
    waivers = _claim001_waivers_by_symref(edges)
    found: list[Violation] = []
    for sym in parsed.symbols:
        v = _claim_violation(rel, parsed.path, sym, bound, waivers)
        if v is not None:
            found.append(v)
    return found, True


# frob:ticket T-4116
# frob:doc docs/modules/gates.md#claim001-t-4116
def claim_lint_gate(root: Path) -> list[Violation]:
    """CLAIM001: flag every function/method/class docstring using
    never/always/idempotent-shaped language with no `frob:invariant`
    directive anywhere in that same symbol's own span (see module
    docstring for the exact symref-matching contract and why this is a
    directive-presence check, never a code-behavior check)."""
    violations: list[Violation] = []
    examined = 0
    for f in iter_files(root, suffix=".py"):
        found, ok = _claim_violations_for_file(f, root)
        if not ok:
            continue
        examined += 1
        violations.extend(found)
    _log.info(
        "claim_lint: %d CLAIM001 violation(s) over %d examined file(s)",
        len(violations),
        examined,
    )
    return violations

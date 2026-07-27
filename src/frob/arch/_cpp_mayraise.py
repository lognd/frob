"""C++ may-throw analysis (T-0687, child 2 of T-0685's exception may-raise
umbrella): the SAME may-set shape T-0686's Python resolver
(`frob.arch._mayraise`) and T-0690's pyo3-boundary scan
(`frob.arch._ffi`) already establish, applied to C++'s own exception
model -- explicit `throw` sites, resolved same-file callee propagation, a
curated std-library thrower table (`vector::at`, `new`, `std::stoi`, ...),
and Unknown fail-closed for anything this module cannot statically
resolve (virtual/indirect/function-pointer calls, per T-0665's
established obligation-pattern precedent for exactly this class of
"cannot see through this call" gap).

`noexcept` FUNCTIONS ARE HARD BOUNDARIES, not advisory ones: a `noexcept`
function whose computed may-throw set is non-empty (a real type, or
Unknown) escapes to `std::terminate` at runtime the instant that
exception actually propagates -- this is not a style preference a team
can waive away, unlike every other `ArchCategory` in this package. The
one thing that DOES discharge it is a `try { ... } catch (...) { ... }`
inside the function that plausibly covers the may-throw call (the SAME
whole-function, not block-scoped, catch-all doctrine
`frob.gates._exhaustive_handling`'s EXHAUST001 already uses for Python's
`Unknown` -- same disclosed limitation, not a new one).

RAW-TEXT SCAN, NOT A TREE-SITTER NODE WALK (deliberate, mirroring
`frob.arch._ffi`'s own choice for the SAME reason): no
`NormalizedModule`/`NormalizedFunction` adapter exists for C++ today
(`frob.arch._cpp`'s existing long-function/god-class checks are
themselves tree-sitter node walks, not model-adapter output) and standing
one up is a much larger, cross-cutting change than this ticket's own
declared `src/frob/arch/**`/`src/frob/lang/**`/`tests/unit/test_arch.py`
scope justifies for one new check family. A brace-depth-tracked raw scan
answers "does this function's body contain a throw/thrower-call/
unresolved-call, and does it have a catch-all" exactly as reliably as a
node walk would for this specific question, at a fraction of the
implementation cost -- the same "cheapest correct tool per question"
house convention `frob.arch._ffi`'s own module docstring already
documents for this package.

SEVERITY: findings use `ArchSeverity` `"error"` (T-0687 added this value
-- see `frob.arch._models`'s own module-level comment for why), not
`"warning"`/`"suggestion"` -- but promoting an `"error"`-severity
`ArchSuggestion` into an enforced, unwaivable GATE finding is
`src/frob/gates/**` wiring, out of this ticket's declared scope; see this
module's own `check_cpp_noexcept_violations` docstring for the disclosed
follow-up, same T-0728/T-0688 "built and tested first, wiring later"
precedent this package already uses repeatedly.

FULL SOUNDNESS NEEDS libclang EVENTUALLY (disclosed, per the parent
ticket's own acceptance text): a tree-sitter-level text scan cannot
resolve overload sets, template instantiation, or cross-translation-unit
calls -- this module's own Unknown-fail-closed default is the
approximation the parent ticket explicitly asked for instead ("the
tree-sitter approximation with fail-closed unknowns is the
deliverable"), not a placeholder for something more precise landing
later in THIS ticket."""
# frob:waive INV006 reason="this module's 'only' occurrences are source-level \
# design-rationale prose (the module docstring's scope/severity/soundness \
# disclosures, mirroring frob.arch._ffi and frob.gates._exhaustive_handling's \
# own module docstrings), verifiable by reading the function it annotates, not \
# a separate cross-module contract needing its own tracked invariant"

from __future__ import annotations

import re

from pydantic import BaseModel

from frob.arch._models import ArchSuggestion
from frob.logging import get_logger

_log = get_logger(__name__)

#: Sentinel raised-type name (T-0687) for a call this module could not
#: statically resolve to either a same-file function or a curated
#: thrower -- fail-closed, matching `frob.arch._mayraise.UNKNOWN`'s own
#: doctrine one language over.
# frob:doc docs/modules/arch.md#cpp-may-throw-analysis-t-0687
# frob:ticket T-0687
UNKNOWN = "Unknown"

#: Curated STL/language thrower table (T-0687), keyed on a text pattern
#: that appears at a call site, mapped to the exception type it is known
#: to throw. `.at(` covers both `std::vector`/`std::map`/... member
#: `.at()` (out_of_range for vector/deque/string, out_of_range for map
#: too -- curated as one type since this is a text scan, not an
#: overload-resolved one) and `new` (bad_alloc on allocation failure) and
#: the `std::sto*` numeric-parse family (invalid_argument/out_of_range,
#: curated as invalid_argument -- the more common failure mode in
#: practice). Extend as more curated stdlib throwing surface is
#: identified; anything NOT listed here that is also not a same-file
#: function is Unknown, fail-closed (this module's own doctrine).
# frob:ticket T-0687
_STL_THROWERS: dict[str, str] = {
    ".at(": "out_of_range",
    "std::stoi(": "invalid_argument",
    "std::stol(": "invalid_argument",
    "std::stoll(": "invalid_argument",
    "std::stoul(": "invalid_argument",
    "std::stoull(": "invalid_argument",
    "std::stof(": "invalid_argument",
    "std::stod(": "invalid_argument",
    "std::stold(": "invalid_argument",
}

#: Matches a bare `new` allocation expression (T-0687) -- `new Type(...)`/
#: `new Type[...]`, which throws `bad_alloc` on allocation failure. Kept
#: as its own regex (not folded into `_STL_THROWERS`'s substring table)
#: since `new` needs a word boundary (`renew`/`newline` must not match).
_NEW_EXPR_RE = re.compile(r"\bnew\s+[A-Za-z_]")

#: Matches a `throw` statement (T-0687) -- both `throw SomeType(...)`
#: (explicit type, captured in group 1 when present) and a bare `throw;`
#: re-throw (group 1 is `None`, resolved to `UNKNOWN` -- this module does
#: not track an enclosing `catch` clause's caught type the way
#: `frob.arch._mayraise._nearest_preceding_catch` does for Python;
#: disclosed narrower than the Python resolver for this one shape).
_THROW_RE = re.compile(r"\bthrow\b\s*([A-Za-z_]\w*(?:::\w+)*)?")

#: Matches a function definition's signature start (T-0687): return type
#: (kept ungrouped, not needed), name, and the opening `(` of its
#: parameter list. Deliberately permissive (does not attempt to parse
#: template parameter lists, `constexpr`/`virtual`/`static` qualifiers,
#: or namespacing) -- a text scan asking "where does the NEXT function
#: body start" needs only the name and the following brace, not a full
#: signature parse.
_FN_SIG_RE = re.compile(r"^[\w:<>,&*\s~]+?\b(\w+)\s*\([^;{]*\)\s*([\w\s]*)\{")

#: Matches `noexcept` in a function signature's trailing qualifier text
#: (T-0687, `_FN_SIG_RE`'s second group) -- `noexcept` and `noexcept(true)`
#: both mark a hard boundary; `noexcept(false)` explicitly opts back into
#: throwing and must NOT match (checked via `_is_noexcept` below, not this
#: regex alone).
_NOEXCEPT_RE = re.compile(r"\bnoexcept\b")

#: Matches `noexcept(false)` specifically (T-0687) -- the one spelling
#: `_NOEXCEPT_RE` would otherwise false-positive on; checked first by
#: `_is_noexcept`.
_NOEXCEPT_FALSE_RE = re.compile(r"\bnoexcept\s*\(\s*false\s*\)")

#: Matches a catch-all clause (T-0687): `catch (...)` -- the only C++
#: catch clause broad enough to plausibly discharge an `UNKNOWN`
#: (mirrors `frob.gates._exhaustive_handling._CATCH_ALL_TYPES`'s own
#: doctrine for Python's bare `except:`/`except Exception:`).
_CATCH_ALL_RE = re.compile(r"\bcatch\s*\(\s*\.\.\.\s*\)")

#: Matches a call expression's callee text immediately before an opening
#: `(` (T-0687) -- `name(` or `obj.name(`/`obj->name(`/`ns::name(`,
#: capturing the bare trailing identifier (group 1). Used to find
#: same-file callee references for the fixpoint propagation pass.
_CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")

#: C++ keywords that can precede `(` and would otherwise false-positive
#: as a "call" under `_CALL_RE` (T-0687) -- control-flow keywords,
#: casts, and `sizeof`/`alignof`/`static_assert` are not calls to a
#: same-file function or a curated thrower, and must not be treated as
#: an unresolved-callee Unknown contribution.
_NOT_A_CALL = frozenset(
    {
        "if",
        "for",
        "while",
        "switch",
        "catch",
        "sizeof",
        "alignof",
        "static_assert",
        "return",
        "throw",
        "new",
        "delete",
        "noexcept",
        "decltype",
        "typeid",
        "static_cast",
        "dynamic_cast",
        "const_cast",
        "reinterpret_cast",
    }
)


# frob:doc docs/modules/arch.md#cpp-may-throw-analysis-t-0687
# frob:ticket T-0687
class CppFunctionRaises(BaseModel):
    """One C++ function's computed may-throw set (T-0687): its name, the
    source line its signature starts on, whether it is `noexcept`,
    whether it has an encompassing `catch (...)` anywhere in its body
    (`has_catch_all`), and the `raises` set (`UNKNOWN` included when any
    contributing throw/call could not be statically resolved) -- the same
    shape `frob.arch._mayraise.FunctionMayRaise` establishes for Python,
    one field added (`is_noexcept`) since C++'s hard-boundary obligation
    (unlike Python's advisory EXHAUST001/002) hangs directly off it."""

    model_config = {}

    name: str
    line: int
    is_noexcept: bool
    has_catch_all: bool
    raises: frozenset[str]


def _is_noexcept(qualifiers: str) -> bool:
    """True when a function signature's trailing qualifier text
    (`_FN_SIG_RE`'s second capture group) marks it `noexcept`/
    `noexcept(true)` -- `noexcept(false)` (checked first) explicitly
    opts back into throwing and is never treated as noexcept (T-0687)."""
    if _NOEXCEPT_FALSE_RE.search(qualifiers):
        return False
    return bool(_NOEXCEPT_RE.search(qualifiers))


def _function_body_span(lines: list[str], sig_line_idx: int) -> tuple[int, int]:
    """The `[start, end)` line-index span of the function body whose
    signature line is `lines[sig_line_idx]` (T-0687) -- brace-depth
    tracked from that line's own `{` (the signature line itself may
    contain balanced braces in a default member initializer or lambda
    default argument) until depth returns to zero. `end` is EXCLUSIVE
    (one past the closing `}`'s line), matching python slice convention."""
    depth = 0
    started = False
    k = sig_line_idx
    n = len(lines)
    while k < n:
        for ch in lines[k]:
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
        if started and depth <= 0:
            return (sig_line_idx, k + 1)
        k += 1
    return (sig_line_idx, n)


def _scan_body_raises(
    body_lines: list[str], name_to_line: dict[str, int]
) -> tuple[frozenset[str], bool]:
    """A function body's own `(raises, has_catch_all)` (T-0687), BEFORE
    same-file callee fixpoint propagation: explicit `throw` sites, curated
    STL-thrower/`new`-expression calls, same-file function references
    (deferred to the caller's fixpoint, contribute nothing directly
    here), and everything else -- fails closed to `UNKNOWN`. A same-file
    function call contributes nothing at THIS stage since its own
    raise-set may not be known yet (same iterative-fixpoint shape
    `frob.arch._mayraise.compute_may_raise` uses for Python's callee
    propagation)."""
    raises: set[str] = set()
    has_catch_all = False
    for line in body_lines:
        if _CATCH_ALL_RE.search(line):
            has_catch_all = True
        for m in _THROW_RE.finditer(line):
            raises.add(m.group(1) if m.group(1) else UNKNOWN)
        if _NEW_EXPR_RE.search(line):
            raises.add("bad_alloc")
        for needle, exc_type in _STL_THROWERS.items():
            if needle in line:
                raises.add(exc_type)
        for cm in _CALL_RE.finditer(line):
            callee = cm.group(1)
            if callee in _NOT_A_CALL:
                continue
            if callee in name_to_line:
                continue  # same-file function -- resolved by the fixpoint below
            # Anything else (STL calls already curated above, unresolved
            # third-party/virtual/indirect calls) that is not a recognized
            # thrower and not a same-file function is fail-closed Unknown
            # -- but only once: a curated thrower needle match above
            # (".at(", "std::stoi(", ...) already accounted for its own
            # call, so re-flagging the SAME call as Unknown here would
            # double-count. Curated needles are substrings ending in "(",
            # exactly what `_CALL_RE` also matches on, so check the
            # curated set (and the plain "new" keyword, never a real
            # callee name) before falling to Unknown.
            if callee == "new" or any(
                needle.endswith(f"{callee}(") for needle in _STL_THROWERS
            ):
                continue
            raises.add(UNKNOWN)
    return frozenset(raises), has_catch_all


# frob:doc docs/modules/arch.md#cpp-may-throw-analysis-t-0687
# frob:ticket T-0687
# frob:tests tests/unit/test_arch.py::TestCppMayThrow.test_noexcept_calling_throwing_function_fires_error  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestCppMayThrow.test_noexcept_calling_vector_at_fires_curated_thrower  # noqa: E501
def scan_cpp_functions(source: str) -> tuple[CppFunctionRaises, ...]:
    """Every function DEFINITION (a signature followed by `{`, not a bare
    declaration ending in `;`) in `source` (T-0687, C++ source text) with
    its computed may-throw set: `_scan_body_raises` per function, then an
    iterative fixpoint over same-file callee references (mirroring
    `frob.arch._mayraise.compute_may_raise`'s own fixpoint shape) so a
    function that calls another same-file function inherits whatever that
    callee may throw, converging once no function's raise set grows
    further (bounded by the number of distinct raised-type names, so this
    always terminates).

    MODEL LIMIT (disclosed, same class as `frob.arch._mayraise`'s own):
    overload resolution, templates, and cross-translation-unit calls are
    invisible to this scan -- a same-file NAME match is enough for
    resolution here (matching this file's own bare-identifier convention,
    the same one T-0686's Python resolver already discloses for its
    same-module lookup)."""
    lines = source.splitlines()
    sig_lines = _find_signature_lines(lines)
    name_to_line = {name: idx for idx, name, _q in sig_lines}
    per_func = _scan_each_function(lines, sig_lines, name_to_line)
    resolved = _propagate_callee_raises(per_func)

    return tuple(
        CppFunctionRaises(
            name=name,
            line=info.line,
            is_noexcept=info.is_noexcept,
            has_catch_all=info.has_catch_all,
            raises=frozenset(resolved[name]),
        )
        for name, info in per_func.items()
    )


class _PerFunctionScan(BaseModel):
    """One function's own scan result BEFORE callee-graph fixpoint
    propagation (T-1034, split out of `scan_cpp_functions` to clear
    ARCH001's 60-line threshold) -- `_scan_each_function`'s per-name
    output, consumed by `_propagate_callee_raises`."""

    model_config = {}

    line: int
    is_noexcept: bool
    has_catch_all: bool
    own_raises: frozenset[str]
    calls: frozenset[str]


def _find_signature_lines(lines: list[str]) -> list[tuple[int, str, str]]:
    """Every `_FN_SIG_RE`-matching signature line in `lines` (T-1034,
    split out of `scan_cpp_functions`), as `(line_idx, name, qualifiers)`
    triples in source order."""
    sig_lines: list[tuple[int, str, str]] = []
    for idx, line in enumerate(lines):
        m = _FN_SIG_RE.match(line)
        if m is None:
            continue
        sig_lines.append((idx, m.group(1), m.group(2)))
    return sig_lines


def _scan_each_function(
    lines: list[str],
    sig_lines: list[tuple[int, str, str]],
    name_to_line: dict[str, int],
) -> dict[str, _PerFunctionScan]:
    """Every function's own `_PerFunctionScan` (T-1034, split out of
    `scan_cpp_functions`): body span, own raise set, catch-all presence,
    `noexcept`-ness, and the same-file callee names its body references
    (deferred to `_propagate_callee_raises`'s fixpoint, not recursed into
    here)."""
    out: dict[str, _PerFunctionScan] = {}
    for idx, name, qualifiers in sig_lines:
        start, end = _function_body_span(lines, idx)
        body = lines[start:end]
        raises, has_catch = _scan_body_raises(body, name_to_line)
        called: set[str] = set()
        for line in body:
            for cm in _CALL_RE.finditer(line):
                callee = cm.group(1)
                if callee in name_to_line and callee != name:
                    called.add(callee)
        out[name] = _PerFunctionScan(
            line=idx + 1,
            is_noexcept=_is_noexcept(qualifiers),
            has_catch_all=has_catch,
            own_raises=raises,
            calls=frozenset(called),
        )
    return out


def _propagate_callee_raises(
    per_func: dict[str, _PerFunctionScan],
) -> dict[str, set[str]]:
    """The same-file callee-graph fixpoint (T-1034, split out of
    `scan_cpp_functions`): each function starts at its own raise set and
    inherits every callee's raise set, repeating until nothing grows --
    mirrors `frob.arch._mayraise.compute_may_raise`'s own fixpoint shape."""
    resolved: dict[str, set[str]] = {
        name: set(info.own_raises) for name, info in per_func.items()
    }
    changed = True
    while changed:
        changed = False
        for name, info in per_func.items():
            for callee in info.calls:
                new_types = resolved.get(callee, set()) - resolved[name]
                if new_types:
                    resolved[name] |= new_types
                    changed = True
    return resolved


# frob:doc docs/modules/arch.md#cpp-may-throw-analysis-t-0687
# frob:ticket T-0687
# frob:tests tests/unit/test_arch.py::TestCppMayThrow.test_noexcept_calling_throwing_function_fires_error  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestCppMayThrow.test_noexcept_with_catch_all_does_not_fire  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestCppMayThrow.test_non_noexcept_function_never_fires  # noqa: E501
def check_cpp_noexcept_violations(
    source: str, rel: str, suggestions: list[ArchSuggestion]
) -> None:
    """Appends an `ArchSuggestion` (category `cpp-noexcept-throws`,
    severity `"error"`) to `suggestions` for every `noexcept` function in
    `source` whose computed may-throw set (`scan_cpp_functions`) is
    non-empty and not discharged by its own `has_catch_all` (T-0687's
    hard-boundary obligation -- see this module's docstring). The escaping
    type(s) are named in the message (the parent ticket's own acceptance:
    "an error finding names the call site").

    Wired into `frob.arch.analyze_project`'s live per-file `"cpp"`
    dispatch branch (`frob.arch.__init__._analyze_one_file`), so a plain
    `frob.arch.analyze_project(root)` call already surfaces these
    findings -- NOT yet promoted into a `src/frob/gates/**` enforced/
    unwaivable gate finding, though, since that wiring is out of this
    ticket's declared scope (`src/frob/arch/**`/`src/frob/lang/**`/
    `tests/unit/test_arch.py` only); see this module's own docstring for
    the disclosed follow-up, same T-0728/T-0688 scope-carve-out
    precedent."""
    for func in scan_cpp_functions(source):
        if not func.is_noexcept:
            continue
        if not func.raises:
            continue
        if func.has_catch_all:
            continue
        suggestions.append(
            ArchSuggestion(
                file=rel,
                line=func.line,
                category="cpp-noexcept-throws",
                severity="error",
                message=(
                    f"cpp-noexcept-throws: `{func.name}` is noexcept but may "
                    f"throw {sorted(func.raises)} -- an escaping exception "
                    "here is std::terminate at runtime; catch it "
                    "(`catch (...)`), fix the throwing call, or drop "
                    "noexcept if this really can fail"
                ),
                symref=f"{rel}::{func.name}",
            )
        )


__all__ = [
    "UNKNOWN",
    "CppFunctionRaises",
    "check_cpp_noexcept_violations",
    "scan_cpp_functions",
]

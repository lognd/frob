"""FFI-boundary exception cross-check (T-0690, child 4 of T-0685's exception
may-raise umbrella): the residual work `frob:callee-raises`
(T-0689/T-0931) and the above-the-def `frob:raises` directive
(`frob.gates._exhaustive_handling`, T-0688) left open -- neither of those
two ALREADY-LANDED conventions cross-checks a pyo3 boundary's Rust-side
observed exception surface against its Python-side declaration, and
neither MANDATES a declaration exist at all on a ctypes/cffi boundary (they
only let one substitute for the resolver's fail-closed `Unknown` when
present). This module supplies both, per the ticket's three-tier user
mandate:

TIER 1 (our own pyo3 crates -- `strata-core`/`frob-core`): the Rust side is
statically visible to us (we own it), so `scan_pyo3_raises` parses each
`#[pyfunction]`'s body for explicit `Py<X>Error::new_err(...)`/
`PyErr::new::<Py<X>Error>(...)` constructions and panic-class sites
(`panic!`/`unreachable!`/`todo!`/`unimplemented!`/`.unwrap()`/`.expect(`,
all of which pyo3 converts into a raised `PanicException` at the Python
call boundary) -- the OBSERVED Rust-side raised-type set. `frob.gates.
_ffi_boundary.ffi_boundary_gate` (FFI001) cross-checks that set against
the corresponding `.pyi` stub's own above-the-def `# frob:raises <Type>`
declarations (`parse_pyi_declared_raises`, the SAME directive
`_exhaustive_handling.py` already owns -- this module does not introduce a
second grammar, just a second CONSUMER of the one T-0688 already ships)
and reports drift as a gate error naming both sides, per the ticket's own
acceptance criterion.

TIER 2 (ctypes/cffi -- no exception-propagation contract exists at all:
errno/return-code convention only, and a C++ exception crossing an
`extern "C"` boundary is `std::terminate`/UB, not something Python could
ever observe as a normal raise): `scan_ctypes_boundary_calls` finds every
call made through a variable this repo's own source bound via
`ctypes.CDLL`/`ctypes.PyDLL`/`ctypes.WinDLL`/`ctypes.OleDLL`/
`ctypes.cdll.LoadLibrary` (and the `pydll`/`windll` siblings) and flags any
such call site missing a same-line callee-raises comment (T-0689's
existing call-site directive, `# frob` + `:callee-raises` -- reused, not
duplicated, as the enforcement target: declaring the empty set via a bare
directive is a VALID, honest "raises nothing, errno convention"
declaration, exactly per the ticket's own acceptance wording). This is a
raw-text scan, deliberately NOT routed through `frob.arch._python`'s
tree-sitter-backed `NormalizedModule` adapter: resolving "which handle
variable does this call's receiver refer to" is ordinary same-function
local-variable binding, cheaper and just as reliable to answer with two
regex passes over the source than by extending the shared normalized
model with a new assignment-tracking event no other check needs (see
`frob.arch._mayraise`'s own module docstring for this package's house
convention of choosing the cheapest correct tool per question rather than
growing one shared model to answer everything).

TIER 3 (third-party compiled modules) is explicitly OUT of this module's
scope per the ticket's own mandate ("declaration optional; Unknown
otherwise") -- `frob.arch._mayraise`'s existing fail-closed `UNKNOWN`
default for any unresolved callee already covers it; nothing here changes
that behavior."""
# frob:waive INV006 reason="this module's 'only' occurrences are source-level \
# design-rationale prose (the module docstring's tier-by-tier mandate summary and \
# per-function docstrings describing already-implemented scan logic), verifiable by \
# reading the function it annotates, not a separate cross-module contract needing its \
# own tracked invariant -- the same INV006 first-turn-on-pool disposition \
# frob.arch._mayraise/_fallibility's own module docstrings already carry"

from __future__ import annotations

import re

from pydantic import BaseModel

from frob.logging import get_logger

_log = get_logger(__name__)

#: `Py<X>Error` pyo3 exception-wrapper type names (T-0690) this module
#: knows how to map onto the equivalent Python builtin exception name --
#: covers every `PyErr::new::<Py<X>Error, _>(...)`/`Py<X>Error::new_err
#: (...)` construction pyo3 itself ships (pyo3's own `exceptions` module),
#: keyed on the `<X>` capture group `_PY_ERROR_RE` extracts. `PyIOError` is
#: pyo3's own historical alias for `PyOSError` (both map to `"OSError"`,
#: matching `_mayraise._EXCEPTION_PARENT`'s own `"OSError"` leaf) --
#: extend as a new pyo3 exception wrapper is actually used in our crates.
# frob:ticket T-0690
_PYO3_ERROR_TYPE_MAP: dict[str, str] = {
    "ValueError": "ValueError",
    "TypeError": "TypeError",
    "RuntimeError": "RuntimeError",
    "KeyError": "KeyError",
    "IndexError": "IndexError",
    "OSError": "OSError",
    "IOError": "OSError",
    "StopIteration": "StopIteration",
    "AttributeError": "AttributeError",
    "NotImplementedError": "NotImplementedError",
    "ImportError": "ImportError",
    "ZeroDivisionError": "ZeroDivisionError",
    "AssertionError": "AssertionError",
    "MemoryError": "MemoryError",
    "OverflowError": "OverflowError",
    "PermissionError": "PermissionError",
    "FileNotFoundError": "FileNotFoundError",
    "UnicodeDecodeError": "UnicodeDecodeError",
    "UnicodeEncodeError": "UnicodeEncodeError",
}

#: Matches a `Py<X>Error` spelling anywhere on a line (T-0690) -- both pyo3
#: construction spellings (`PyValueError::new_err(...)` and
#: `PyErr::new::<PyValueError, _>(...)`) contain this exact substring, so
#: one regex over raw source covers both without parsing the call
#: expression shape itself.
_PY_ERROR_RE = re.compile(r"\bPy(\w+?)Error\b")

#: Panic-class Rust macro/method call patterns (T-0690) that pyo3
#: automatically converts into a raised `pyo3::exceptions::
#: PyBaseException` subclass (`PanicException`) crossing the Python call
#: boundary -- an unhandled Rust panic inside a `#[pyfunction]` body never
#: aborts the Python process the way a bare panic would in a pure-Rust
#: binary; pyo3's own `catch_unwind` wrapper around every exported
#: function converts it. Treated as one sentinel type name,
#: `"PanicException"`, rather than trying to recover the panic message's
#: shape statically.
# frob:ticket T-0690
_PANIC_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bpanic!\s*\("),
    re.compile(r"\bunreachable!\s*\("),
    re.compile(r"\btodo!\s*\("),
    re.compile(r"\bunimplemented!\s*\("),
    re.compile(r"\.unwrap\(\)"),
    re.compile(r"\.expect\("),
)

#: Matches a `#[pyfunction]` attribute line (T-0690) -- the pyo3 marker
#: `scan_pyo3_raises` uses to find the start of each exported function; a
#: following `#[pyo3(...)]` attribute line (signature overrides etc.) is
#: skipped over, not treated as the function's own start.
_PYFUNCTION_ATTR_RE = re.compile(r"^\s*#\[pyfunction\]")

#: Matches the `fn NAME(` line that begins a function body (T-0690, used
#: after a `#[pyfunction]`/`#[pyo3(...)]` attribute run) -- captures the
#: bare function name pyo3 exposes to Python unchanged (no `#[pyo3(name =
#: ...)]` rename support; not observed in either crate today, and adding
#: it is a narrow follow-up if one ever appears).
_FN_NAME_RE = re.compile(r"^\s*(?:pub\s+)?fn\s+(\w+)\s*\(")

#: The above-the-def `# frob:raises <ExceptionType>` directive prefix
#: (T-0690) -- the SAME directive `frob.gates._exhaustive_handling`
#: already owns (T-0688), reused here as the `.pyi` stub's declaration
#: surface rather than introduced as a second grammar; kept as a literal
#: duplicate of that module's private `_DIRECTIVE_PREFIX` constant since
#: importing a private name across these two modules is the wrong
#: coupling for one three-word string (same house convention
#: `_exhaustive_handling.py`'s own `_qualname` duplicate-of-`_mayraise`
#: precedent already establishes).
_DIRECTIVE_PREFIX = "# frob:raises "

#: How many source lines directly above a `.pyi` function's `def` line
#: (T-0690) this module scans for `_DIRECTIVE_PREFIX` comments -- mirrors
#: `_exhaustive_handling._DIRECTIVE_LOOKBACK_LINES`.
_DIRECTIVE_LOOKBACK_LINES = 15

#: Matches a `.pyi` stub's `def NAME(` line (T-0690) -- deliberately not
#: requiring `-> ...: ...` on the same line, since a stub's return-type
#: annotation may itself wrap onto following lines for a long signature.
_PYI_DEF_RE = re.compile(r"^\s*def\s+(\w+)\s*\(")

#: ctypes handle-loading call patterns (T-0690) whose LHS binds a library
#: handle -- a call made THROUGH that handle (`handle.some_c_func(...)`)
#: is the opaque cross-language boundary this module enforces a
#: declaration on; the loading call itself is not (it raises ordinary,
#: already-modeled `OSError`, not an opaque C-side exception). Matches
#: `ctypes.CDLL(...)`/`ctypes.PyDLL(...)`/`ctypes.WinDLL(...)`/
#: `ctypes.OleDLL(...)` and the `ctypes.cdll`/`ctypes.pydll`/
#: `ctypes.windll` singleton's own `.LoadLibrary(...)` method.
_CTYPES_LOAD_RE = re.compile(
    r"\b(\w+)\s*=\s*ctypes\."
    r"(?:CDLL|PyDLL|WinDLL|OleDLL|cdll\.LoadLibrary|pydll\.LoadLibrary|"
    r"windll\.LoadLibrary)\s*\("
)

#: Matches a call made through a bound ctypes handle variable (T-0690) --
#: `{handle}.some_c_function(`. Built per-handle by `scan_ctypes_boundary_
#: calls` (the handle name is only known after `_CTYPES_LOAD_RE` finds
#: it), so this is a format template, not a compiled pattern.
_CTYPES_CALL_TEMPLATE = r"\b{handle}\.(\w+)\s*\("

#: Matches a `# frob:callee-raises` declaration comment anywhere on a line
#: (T-0690) -- the SAME call-site directive `frob.arch._python`'s
#: `_FROB_RAISES_RE` already parses (T-0689, renamed by T-0931); this
#: module only needs to know PRESENCE on the call's own line (the
#: enforcement question), not the declared set itself, so a narrower
#: presence-only regex is enough here.
_CALLEE_RAISES_PRESENT_RE = re.compile(r"#\s*frob:callee-raises\b")


# frob:doc docs/modules/gates.md#ffi001-ffi002-t-0690
# frob:ticket T-0690
class PyO3FunctionRaises(BaseModel):
    """One `#[pyfunction]`'s observed Rust-side raised-type set (T-0690):
    its exported name (the Python-visible callable name), the source line
    its `fn` keyword starts on, and the `Py<X>Error`/panic-class exception
    names `scan_pyo3_raises` found inside its body. Empty `raises` means
    the scan found no explicit error construction or panic-class call --
    NOT a guarantee the function cannot raise (an `Err(...)` propagated
    from a callee this raw scan does not recurse into is invisible to it;
    see `scan_pyo3_raises`'s own docstring)."""

    model_config = {}

    name: str
    line: int
    raises: frozenset[str]


def _map_pyo3_error(raw: str) -> str | None:
    """Maps a `Py<X>Error` capture (T-0690, `raw` is `_PY_ERROR_RE`'s `<X>`
    group with the trailing `Error` already stripped) onto its Python
    builtin exception name via `_PYO3_ERROR_TYPE_MAP`, or `None` for a
    `Py<X>Error` spelling this module does not curate (a pyo3 exception
    wrapper this repo's crates have never actually used) -- fail-open on
    an unrecognized wrapper name rather than inventing a type text no
    Python exception hierarchy actually has, matching this module's own
    disclosed narrow-curation posture (see the module docstring's
    `_PYO3_ERROR_TYPE_MAP` entry)."""
    return _PYO3_ERROR_TYPE_MAP.get(f"{raw}Error")


# frob:doc docs/modules/gates.md#ffi001-ffi002-t-0690
# frob:ticket T-0690
# frob:tests tests/test_gates.py::TestFfiBoundaryGate.test_pyo3_drift_fires_ffi001
# frob:tests tests/test_gates.py::TestFfiBoundaryGate.test_pyo3_declared_matches_no_drift  # noqa: E501
def scan_pyo3_raises(source: str) -> tuple[PyO3FunctionRaises, ...]:
    """Every `#[pyfunction]` in `source` (T-0690, Rust source text) with its
    OBSERVED raised-type set: a raw brace-depth-tracked scan (not a full
    tree-sitter parse -- this module deliberately stays independent of
    `frob.arch._rust`'s `NormalizedModule` adapter, which has no
    `#[pyfunction]`-attribute field to find these by; adding one is a
    larger, cross-cutting model change out of this ticket's declared
    scope, noted in its Done report) that finds the `fn NAME(` line
    following a `#[pyfunction]` attribute (skipping any intervening
    `#[pyo3(...)]` attribute lines), then walks forward counting `{`/`}`
    to find the matching function body and applies `_PY_ERROR_RE`/
    `_PANIC_PATTERNS` over every line inside it.

    MODEL LIMIT (disclosed, matching this package's house convention): an
    `Err(...)`/panic raised by a CALLEE this function invokes, rather than
    directly in its own body, is invisible to this scan -- same
    same-function-only limit `frob.arch._mayraise`'s own `direct_raises`
    already discloses for the Python side, not a regression introduced
    here."""
    lines = source.splitlines()
    out: list[PyO3FunctionRaises] = []
    i = 0
    n = len(lines)
    while i < n:
        if not _PYFUNCTION_ATTR_RE.match(lines[i]):
            i += 1
            continue
        j = i + 1
        while j < n and lines[j].lstrip().startswith("#["):
            j += 1
        while j < n and not lines[j].strip():
            j += 1
        if j >= n:
            break
        m = _FN_NAME_RE.match(lines[j])
        if m is None:
            i = j + 1
            continue
        name = m.group(1)
        fn_line = j + 1  # 1-indexed
        raises = _scan_function_body(lines, j)
        out.append(PyO3FunctionRaises(name=name, line=fn_line, raises=raises))
        i = j + 1
    return tuple(out)


def _scan_function_body(lines: list[str], start: int) -> frozenset[str]:
    """The raised-type set found inside the function whose `fn` line is
    `lines[start]` (T-0690): walks forward tracking brace depth from that
    line's own `{` (a signature may itself contain balanced `{`/`}` in a
    generic bound or default value, which is why depth-from-the-`fn`-line
    is tracked rather than assuming the body starts on the very next
    line) until depth returns to zero, applying `_PY_ERROR_RE`/
    `_PANIC_PATTERNS` to every line visited."""
    raises: set[str] = set()
    depth = 0
    started = False
    k = start
    n = len(lines)
    while k < n:
        line = lines[k]
        # frob:waive PERF003 reason="single per-character brace-depth scan, not a \
        # compare-every-pair nested search -- each line's characters are visited once \
        # each to track depth; there is no second collection to index this against"
        for ch in line:
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
        for pat in _PANIC_PATTERNS:
            if pat.search(line):
                raises.add("PanicException")
        for pm in _PY_ERROR_RE.finditer(line):
            mapped = _map_pyo3_error(pm.group(1))
            if mapped is not None:
                raises.add(mapped)
        if started and depth <= 0:
            break
        k += 1
    return frozenset(raises)


# frob:doc docs/modules/gates.md#ffi001-ffi002-t-0690
# frob:ticket T-0690
# frob:tests tests/test_gates.py::TestFfiBoundaryGate.test_pyo3_drift_fires_ffi001
# frob:tests tests/test_gates.py::TestFfiBoundaryGate.test_pyo3_declared_matches_no_drift  # noqa: E501
def parse_pyi_declared_raises(source: str) -> dict[str, frozenset[str]]:
    """Every `.pyi` stub function's declared `# frob:raises <Type>` set
    (T-0690), keyed on function name -- the SAME above-the-def directive
    `frob.gates._exhaustive_handling` already owns (T-0688), reused here
    as the pyo3 boundary's Python-side declaration surface
    (`frob.gates._ffi_boundary.ffi_boundary_gate`'s FFI001 cross-checks
    this against `scan_pyo3_raises`'s Rust-side observed set). A function
    with no directive lines above it is simply absent from the returned
    mapping (an empty declared set and "never declared" are NOT the same
    thing here -- FFI001 treats both as "nothing declared", but callers
    needing the distinction can check membership directly)."""
    lines = source.splitlines()
    declared: dict[str, frozenset[str]] = {}
    for idx, line in enumerate(lines):
        m = _PYI_DEF_RE.match(line)
        if m is None:
            continue
        name = m.group(1)
        start = max(0, idx - _DIRECTIVE_LOOKBACK_LINES)
        types: set[str] = set()
        for raw in lines[start:idx]:
            text = raw.strip()
            if text.startswith(_DIRECTIVE_PREFIX):
                types.add(text[len(_DIRECTIVE_PREFIX) :].strip())
        if types:
            declared[name] = frozenset(types)
    return declared


# frob:doc docs/modules/gates.md#ffi001-ffi002-t-0690
# frob:ticket T-0690
class CtypesBoundaryCall(BaseModel):
    """One call made through a ctypes-loaded library handle (T-0690):
    `handle` is the local variable `scan_ctypes_boundary_calls` traced back
    to a `ctypes.CDLL`-family loading call, `callee` is the attribute name
    invoked on it, `line` is the 1-indexed source line, and `declared` is
    whether that same line already carries a `# frob:callee-raises`
    comment (T-0689's existing call-site directive) -- `ffi_boundary_gate`
    (FFI002) flags every entry where `declared` is `False`."""

    model_config = {}

    handle: str
    callee: str
    line: int
    declared: bool


# frob:doc docs/modules/gates.md#ffi001-ffi002-t-0690
# frob:ticket T-0690
# frob:tests tests/test_gates.py::TestFfiBoundaryGate.test_ctypes_call_without_declaration_fires_ffi002  # noqa: E501
# frob:tests tests/test_gates.py::TestFfiBoundaryGate.test_ctypes_call_with_empty_declaration_clean  # noqa: E501
def scan_ctypes_boundary_calls(source: str) -> tuple[CtypesBoundaryCall, ...]:
    """Every call made through a ctypes-loaded library handle in `source`
    (T-0690, python source text): first finds every `handle =
    ctypes.CDLL(...)`-family binding (`_CTYPES_LOAD_RE`), then scans the
    WHOLE file (not just lines after the binding -- a handle may be
    reassigned/re-loaded, and this module does not attempt control-flow
    ordering; matching by name anywhere in the file is the same
    deliberately coarse, whole-function/whole-file proxy convention this
    package's raw-source directive scans already use, e.g.
    `_exhaustive_handling._declared_propagations`'s bounded-but-textual
    lookback) for `{handle}.method(` call sites, recording whether each
    one's own line already carries a `# frob:callee-raises` declaration.

    A handle name that collides with an unrelated same-named local
    variable elsewhere in the file is a disclosed false-positive risk
    (textual, not scope-aware matching) -- acceptable per this module's
    own house convention of favoring a cheap, fail-loud textual scan over
    a full binding-resolution pass for a narrow enforcement question (see
    the module docstring)."""
    lines = source.splitlines()
    handles: set[str] = set()
    for line in lines:
        for m in _CTYPES_LOAD_RE.finditer(line):
            handles.add(m.group(1))

    out: list[CtypesBoundaryCall] = []
    if not handles:
        return tuple(out)

    for handle in sorted(handles):
        call_re = re.compile(_CTYPES_CALL_TEMPLATE.format(handle=re.escape(handle)))
        for idx, line in enumerate(lines):
            for m in call_re.finditer(line):
                callee = m.group(1)
                if callee in {"LoadLibrary"}:
                    continue
                declared = bool(_CALLEE_RAISES_PRESENT_RE.search(line))
                out.append(
                    CtypesBoundaryCall(
                        handle=handle,
                        callee=callee,
                        line=idx + 1,
                        declared=declared,
                    )
                )
    return tuple(out)


__all__ = [
    "CtypesBoundaryCall",
    "PyO3FunctionRaises",
    "parse_pyi_declared_raises",
    "scan_ctypes_boundary_calls",
    "scan_pyo3_raises",
]

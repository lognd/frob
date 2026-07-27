"""EXHAUST001/EXHAUST002: the exhaustive-exception gate (T-0688, child 3 of
T-0685's exception may-raise umbrella) over `frob.arch._mayraise.
compute_may_raise`'s per-function may-raise sets (T-0686). This module
consumes that resolver's PUBLIC surface only (`compute_may_raise`,
`UNKNOWN`) and never edits `_mayraise.py` itself -- a sibling ticket
(T-0689) concurrently extends that resolver for ctypes boundaries, and
T-0688's own declared scope carves it out.

A function that already attempts exception handling (at least one
`except`/`catch` clause -- `NormalizedFunction.catches`) is treated as a
declared BOUNDARY: this gate asks whether that boundary's handling is
EXHAUSTIVE over its own guarded may-raise set. `compute_may_raise`'s
`FunctionMayRaise.raises` is already the LEAKED remainder after that
function's own catches are subtracted (see `_mayraise.compute_may_raise`'s
own docstring: `direct_raises` always escapes, `catchable`/callee-exposed
types are filtered by the function's own catches) -- so any non-empty
leaked set on a function that HAS a catch clause is, by construction, an
incompletely-handled boundary. A function with NO catch clause at all is
not a "boundary" by this gate's definition (it is just propagating, which
is normal and not flagged here) -- see `frob.arch._exceptions.
check_errors_as_values` for the sibling advisory that instead looks at
public raisers with unhandling callers, a different question over the
same computed sets.

EXHAUST001 (Unknown leaks past a boundary with no catch-all): `UNKNOWN` in
the leaked set means some raise/callee this resolver could not statically
identify escapes a function that otherwise tries to handle its own
errors, and none of its own catches is broad enough (bare `except:` or
`except Exception:`) to plausibly cover it -- per the parent ticket's own
acceptance, `Unknown` in the guarded set forces a catch-all or fixing the
unresolvable call; silent non-exhaustiveness is not allowed to pass
quietly. A `# frob:raises <Type>` declared-propagation directive (below)
never discharges `UNKNOWN` -- it names a KNOWN type, and `UNKNOWN` is
definitionally not one; only a real catch-all does.

EXHAUST002 (a named, non-`UNKNOWN` type leaks past a boundary): every
leaked type other than `UNKNOWN` is checked against this function's own
`# frob:raises <ExceptionType>` directive comments -- one type per
directive line, placed directly above the function's `def`/decorator
block (the same above-the-def placement convention every other `frob:`
directive in this repo already uses, scanned via `_declared_
propagations`'s bounded lookback window since `NormalizedFunction` itself
carries no raw-comment text). A function that declares it intentionally
propagates `ValueError` is not flagged for `ValueError` leaking -- that is
now an explicit, auditable contract instead of a silent gap. Any leaked
named type with no matching directive is EXHAUST002, naming exactly the
missing type(s) (the parent ticket's own acceptance: "the missing
exception types are named").

Both rules attach `symref` (the leaking function's `path::qualname`) so
`frob:waive EXHAUST001 reason="..."` / `frob:waive EXHAUST002
reason="..."` bind precisely to that one function, same waiver-precision
convention `frob.gates._models.Violation.symref`'s own docstring
describes for every other symbol-scoped rule.

SEVERITY (first-turn-on debt, T-0688): both rules ship at `Severity.WARN`,
not `ERROR`, at this ticket's landing -- a first real run of this gate
against this repo's OWN source (176 findings, overwhelmingly narrow
`except OSError`/`except ValueError`-style catches around a call this
resolver cannot statically resolve, i.e. EXHAUST001) surfaced pre-existing
debt on a scale that would instantly red every other ticket's `frob
check` if promoted straight to ERROR, same shape T-0680's REG008-REG011
and T-0728's own Done report both disclosed for their own first-turn-on
gates. This is a WARN-not-ERROR posture chosen deliberately, not a
softened design -- see the filed follow-up ticket (noted in this ticket's
own Done report) that tracks paying the corpus down before promotion.

SCOPE: python-only, same disclosed limit `compute_may_raise` itself
already carries (its own module docstring) -- a file this gate's own
`raw_tree`/`PythonAdapter` pass cannot parse, or whose language is not
`"python"`, is silently skipped, matching every other `frob.arch`-
consuming gate's disclosed language-coverage gap (e.g.
`frob.gates._protocol_summary`'s own `.py`-only exceptional-exit half).
Test files are excluded (`frob.excludes.is_test_file`) -- a test's own
`pytest.raises`-style exception assertions are not a production boundary
this gate should be scoring."""
# frob:waive INV006 reason="this module's 'only' occurrences are source-level \
# design-rationale prose (the module docstring's model-limit disclosures and \
# per-function docstrings describing already-implemented resolution/matching \
# logic), verifiable by reading the function it annotates, not a separate \
# cross-module contract needing its own tracked invariant -- the same INV006 \
# first-turn-on-pool disposition frob.arch._fallibility/_mayraise's own module \
# docstrings already carry"

from __future__ import annotations

from pathlib import Path

from frob.arch._mayraise import UNKNOWN, compute_may_raise
from frob.arch._normalized import NormalizedFunction, NormalizedModule
from frob.excludes import is_excluded, is_test_file, iter_files, load_exclude_globs
from frob.gates._models import Severity, Violation
from frob.lang import raw_tree
from frob.logging import get_logger

_log = get_logger(__name__)

#: Caught-type texts (T-0688) that count as a "catch-all" broad enough to
#: plausibly discharge `UNKNOWN` -- a bare `except:` (`None`) or an
#: explicit `except Exception:`, matching `frob.arch._mayraise._catches`'
#: own catch-all definition for `UNKNOWN` (duplicated narrowly here since
#: this module consumes only `_mayraise`'s public surface, per this
#: ticket's declared scope carve-out around that private helper).
_CATCH_ALL_TYPES: tuple[str | None, ...] = (None, "Exception")

#: The `# frob:raises <ExceptionType>` declared-propagation directive
#: prefix (T-0688) -- placed directly above a function's `def`/decorator
#: block, the same above-the-def placement every other `frob:` directive
#: in this repo already uses, to mark that the function intentionally lets
#: `<ExceptionType>` escape uncaught rather than leaving that as a silent
#: gap `EXHAUST002` would otherwise flag.
_DIRECTIVE_PREFIX = "# frob:raises "

#: How many source lines directly above a function's `line` (T-0688) this
#: gate scans for `_DIRECTIVE_PREFIX` comments -- generous enough to clear
#: a stack of `frob:ticket`/`frob:doc`/decorator lines above a def without
#: reading unrelated prior code as this function's own directives.
_DIRECTIVE_LOOKBACK_LINES = 15


def _qualname(
    module: NormalizedModule, cls_name: str | None, func: NormalizedFunction
) -> str:
    """`path::Class.method`/`path::function` symref (T-0289's shape,
    T-0688) for `func` -- a narrow local duplicate of
    `frob.arch._mayraise._qualname` (that module's private helper is out
    of this ticket's declared-scope carve-out; see this module's docstring
    for why duplicating this one small helper, not importing a private
    name across modules, is the intended shape here)."""
    if cls_name is None:
        return f"{module.path}::{func.name}"
    return f"{module.path}::{cls_name}.{func.name}"


def _iter_functions(
    module: NormalizedModule,
) -> list[tuple[NormalizedFunction, str]]:
    """Every top-level function and method in `module` (T-0688), paired
    with its `_qualname` -- the same free-functions-then-methods
    enumeration order `frob.arch._mayraise.compute_may_raise` itself
    walks, so lookups against its returned mapping always hit."""
    out: list[tuple[NormalizedFunction, str]] = []
    for f in module.functions:
        out.append((f, _qualname(module, None, f)))
    for c in module.classes:
        for m in c.methods:
            out.append((m, _qualname(module, c.name, m)))
    return out


def _declared_propagations(
    source_lines: list[str], func: NormalizedFunction
) -> set[str]:
    """Exception type names declared via a `# frob:raises <Type>` comment
    (T-0688) directly above `func`'s `line`, within
    `_DIRECTIVE_LOOKBACK_LINES` -- the intentional-propagation contract
    `EXHAUST002` checks a leaked named type against before flagging it."""
    end = max(0, func.line - 1)
    start = max(0, end - _DIRECTIVE_LOOKBACK_LINES)
    declared: set[str] = set()
    for raw in source_lines[start:end]:
        text = raw.strip()
        if text.startswith(_DIRECTIVE_PREFIX):
            declared.add(text[len(_DIRECTIVE_PREFIX) :].strip())
    return declared


def _has_catch_all(func: NormalizedFunction) -> bool:
    """True when `func` has at least one catch-all clause (T-0688,
    `_CATCH_ALL_TYPES`) -- the only thing broad enough to discharge a
    leaked `UNKNOWN`."""
    return any(c.exception_type in _CATCH_ALL_TYPES for c in func.catches)


def _function_violations(
    module: NormalizedModule,
    func: NormalizedFunction,
    qualname: str,
    leaked: frozenset[str],
    source_lines: list[str],
) -> list[Violation]:
    """EXHAUST001/EXHAUST002 for one function (T-0688): `func` with no
    `catches` of its own is not a boundary and is never flagged (this
    gate's module docstring). Otherwise `leaked` (`compute_may_raise`'s
    already-except-subtracted exposed set) is checked for an undischarged
    `UNKNOWN` (EXHAUST001) and any named type absent from `func`'s own
    `# frob:raises` directives (EXHAUST002)."""
    violations: list[Violation] = []
    if not func.catches:
        return violations

    if UNKNOWN in leaked and not _has_catch_all(func):
        violations.append(
            Violation(
                rule="EXHAUST001",
                severity=Severity.WARN,
                file=module.path,
                line=func.line,
                message=(
                    f"EXHAUST001: `{qualname}` handles some exceptions but an "
                    "unresolvable call/raise (Unknown) still escapes -- add a "
                    "catch-all (`except Exception:`) or fix the unresolvable "
                    "call"
                ),
                symref=qualname,
            )
        )

    declared = _declared_propagations(source_lines, func)
    named_leak = {t for t in leaked if t != UNKNOWN} - declared
    if named_leak:
        violations.append(
            Violation(
                rule="EXHAUST002",
                severity=Severity.WARN,
                file=module.path,
                line=func.line,
                message=(
                    f"EXHAUST002: `{qualname}` guards some exceptions but "
                    f"{sorted(named_leak)} still escape uncaught and "
                    "undeclared -- catch them, or declare `# frob:raises "
                    "<Type>` directly above the function to mark intentional "
                    "propagation"
                ),
                symref=qualname,
            )
        )
    return violations


# frob:doc docs/modules/gates.md#exhaust001exhaust002-t-0688
# frob:ticket T-0688
# frob:tests tests/test_gates.py::TestExhaustiveHandlingGate.test_partial_catch_of_named_type_fires_exhaust002  # noqa: E501
# frob:tests tests/test_gates.py::TestExhaustiveHandlingGate.test_unknown_without_catch_all_fires_exhaust001  # noqa: E501
# frob:tests tests/test_gates.py::TestExhaustiveHandlingGate.test_catch_all_of_unknown_does_not_fire_exhaust001  # noqa: E501
# frob:tests tests/test_gates.py::TestExhaustiveHandlingGate.test_declared_frob_raises_directive_discharges_exhaust002  # noqa: E501
# frob:tests tests/test_gates.py::TestExhaustiveHandlingGate.test_function_with_no_catches_is_not_a_boundary  # noqa: E501
def exhaustive_handling_gate(root: Path) -> tuple[Violation, ...]:
    """EXHAUST001/EXHAUST002 (T-0688) over every python file under `root`:
    a function/method that has attempted exception handling (at least one
    `catches` entry) but still leaks an exception past it, per
    `frob.arch._mayraise.compute_may_raise`, fails with the missing type(s)
    named (`_function_violations`). Non-python files, files with no
    tree-sitter grammar, and test files are silently skipped -- see this
    module's docstring for the disclosed scope."""
    from frob.arch._python import PythonAdapter

    exclude_globs = load_exclude_globs(root)
    adapter = PythonAdapter()
    violations: list[Violation] = []

    for path in iter_files(root, suffix=".py"):
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            continue
        if is_excluded(rel, exclude_globs) or is_test_file(rel):
            continue

        parsed = raw_tree(path)
        if parsed.is_err:
            _log.debug("exhaustive_handling_gate: %s not parsed (%s)", rel, parsed.err)
            continue
        tree, _source, language = parsed.danger_ok
        if language != "python":
            continue

        module = adapter.adapt(tree, b"", rel)
        mayraise = compute_may_raise(module)
        try:
            source_lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            _log.debug("exhaustive_handling_gate: cannot read %s: %s", rel, exc)
            source_lines = []

        for func, qualname in _iter_functions(module):
            fmr = mayraise.get(qualname)
            if fmr is None:
                continue
            violations.extend(
                _function_violations(module, func, qualname, fmr.raises, source_lines)
            )

    _log.info("exhaustive_handling_gate: %d violation(s)", len(violations))
    return tuple(violations)


__all__ = ["exhaustive_handling_gate"]

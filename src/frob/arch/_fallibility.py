"""Fallibility-discipline checks (ARCH1xx, T-0623, EPIC T-0330's error-
handling family): unhandled Result, swallowed exception, recoverable-
error-wrong-signature, over-broad except (folded with re-raise-losing-
context, per this ticket's own body text presenting them as one bullet).

WHY here, not `_logging_checks.py`/`_solid.py`: this is its own family in
the epic's catalog (a proxy for "does the code HANDLE its own failure
modes correctly", distinct from T-0622's "does the code SAY anything
when it fails"), so it gets its own module -- the sibling-module-per-
family convention `_solid.py`/`_layering.py`/`_typedesign.py`/
`_logging_checks.py` already established. Every check here is written
once against `frob.arch._normalized.NormalizedModule` (T-0609), same
convention as those siblings -- nothing here parses a `tree_sitter.Tree`
directly.

SCOPE NOTE: `src/frob/arch/_models.py`'s scope lease was free at
implementation time (same as T-0622's), so all four categories below
extend the SHARED `frob.arch._models.ArchCategory`/`ArchSuggestion`
directly -- no local literal, no fold-in follow-up needed.

MODEL-LIMIT DISCLOSURE (T-0609's own scope, not routed around):
`NormalizedCall` has no "is this call's result assigned / passed along /
discarded" field -- the T-0609 model tracks a call's callee/line/args
only, not its surrounding expression context. `check_unhandled_result`
below is therefore a disclosed, best-effort proxy (a bare-statement call
to a same-module Result-returning function whose line is not itself a
`return` statement's line) that can both under- and over-fire relative
to true "value assigned to `_`/discarded" detection -- see that check's
own docstring for the exact proxy and its known false-positive shape
(a call assigned to a local variable looks identical to this model)."""
# frob:waive INV006 reason="this module's 'only' occurrences are source-level \
# design-rationale prose (the module docstring's model-limit disclosure and the \
# per-check docstrings describing what already-implemented text matching does), \
# verifiable by reading the function it annotates, not a separate cross-module \
# contract needing its own tracked invariant -- the same INV006 first-turn-on-pool \
# disposition frob.arch._solid/_typedesign/_logging_checks' own module docstrings \
# already carry"

from __future__ import annotations

from frob.arch._models import ArchSuggestion
from frob.arch._normalized import (
    NormalizedCall,
    NormalizedCatch,
    NormalizedClass,
    NormalizedFunction,
    NormalizedModule,
)

#: Exception type names (T-0623) counted as "clearly recoverable" for
#: `check_recoverable_error_wrong_signature` -- user-input/lookup
#: validation errors a caller can reasonably expect to handle, as opposed
#: to a genuinely-exceptional/programmer-bug error (`AssertionError`,
#: `RuntimeError`, ...) that legitimately stays an exception.
_RECOVERABLE_EXCEPTION_TYPES = frozenset(
    {"ValueError", "KeyError", "LookupError", "TypeError"}
)

#: Callee substrings (T-0623) counted as "this call is a log statement" --
#: the same bare-text heuristic `frob.arch._logging_checks` uses,
#: duplicated narrowly here (one private constant, not exported) since
#: this ticket's own scope does not include that sibling module.
_LOG_CALLEE_MARKERS = ("log.", "logger.", "logging.", "_log.", "_logger.")

#: Line-adjacency window (T-0623) a raise/log/return must fall within,
#: relative to a catch clause's own line, to count as "this catch clause
#: does something with the exception" -- same style of textual proxy
#: `frob.arch._solid`'s guard-clause detectors and `_logging_checks`'s
#: log-adjacency check both use, since this model has no block-scoping
#: finer than a whole function body.
_ADJACENCY_WINDOW = 3


def _qualname(
    module: NormalizedModule, cls: NormalizedClass | None, func: NormalizedFunction
) -> str:
    """`path::Class.method`/`path::function` symref (T-0289's shape,
    T-0623) for `func`, optionally scoped to `cls`."""
    if cls is None:
        return f"{module.path}::{func.name}"
    return f"{module.path}::{cls.name}.{func.name}"


def _bare_callee_name(callee: str) -> str:
    """The trailing identifier of a possibly-dotted callee text (T-0623)
    -- `self.load` / `store.load` / `load` all yield `"load"`, so a
    same-module function lookup does not need call-site receiver
    resolution (out of this model's scope)."""
    return callee.rsplit(".", 1)[-1]


def _is_log_call(call: NormalizedCall) -> bool:
    """True when `call`'s callee text looks like a log statement
    (`_LOG_CALLEE_MARKERS`, T-0623) -- a bare-text heuristic, not a
    resolved-symbol match."""
    callee = call.callee.lower()
    return any(marker in callee for marker in _LOG_CALLEE_MARKERS)


# ---------------------------------------------------------------------------
# unhandled Result (T-0623)
# ---------------------------------------------------------------------------


def _result_returning_names(module: NormalizedModule) -> set[str]:
    """Bare names of every function/method in `module` whose declared
    `return_type` text contains `"Result["` (typani's convention,
    T-0623) -- the same-module lookup table `check_unhandled_result`
    scans call sites against; cross-module Result-returning functions are
    out of scope (this model does not resolve imports)."""
    names: set[str] = set()
    for f in module.functions:
        if f.return_type and "Result[" in f.return_type:
            names.add(f.name)
    for c in module.classes:
        for m in c.methods:
            if m.return_type and "Result[" in m.return_type:
                names.add(m.name)
    return names


# frob:doc docs/modules/arch.md#fallibility-checks
# frob:tests tests/unit/test_arch.py::TestUnhandledResult.test_bare_statement_call_to_result_function_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestUnhandledResult.test_returned_call_to_result_function_not_flagged  # noqa: E501
def check_unhandled_result(module: NormalizedModule) -> list[ArchSuggestion]:
    """Unhandled Result (T-0623): flag a call to a same-module function
    whose `return_type` text contains `"Result["` (`_result_returning_names`)
    when that call's own line is not also one of the caller's `returns`
    lines -- a `return foo()` is the one shape this model can positively
    confirm consumes the value; anything else (including a genuine
    `x = foo()` local assignment, which this model cannot distinguish
    from a discarded bare-statement call -- see this module's docstring)
    is flagged as the disclosed best-effort proxy for "the Result value
    was silently discarded". Written once against `NormalizedModule`, so
    it fires for every `LanguageAdapter`."""
    out: list[ArchSuggestion] = []
    result_names = _result_returning_names(module)
    if not result_names:
        return out

    def _scan(func: NormalizedFunction, qualname: str) -> None:
        return_lines = {r.line for r in func.returns}
        for call in func.calls:
            if _bare_callee_name(call.callee) not in result_names:
                continue
            if call.line in return_lines:
                continue
            out.append(
                ArchSuggestion(
                    file=module.path,
                    line=call.line,
                    category="unhandled-result",
                    severity="suggestion",
                    message=(
                        f"`{qualname}` calls `{call.callee}` (returns Result)"
                        " without using the returned value"
                    ),
                    detail=(
                        "a Result-returning call whose value is not"
                        " returned/propagated may be silently discarding"
                        " an error -- handle the Err case explicitly, or"
                        " return the Result to the caller"
                    ),
                    symref=qualname,
                )
            )

    for f in module.functions:
        _scan(f, f.name)
    for c in module.classes:
        for m in c.methods:
            _scan(m, _qualname(module, c, m))
    return out


# ---------------------------------------------------------------------------
# swallowed exception (T-0623)
# ---------------------------------------------------------------------------


def _catch_does_something(func: NormalizedFunction, catch: NormalizedCatch) -> bool:
    """True when some raise/log-call/return in `func` falls within
    `_ADJACENCY_WINDOW` lines of `catch` (T-0623) -- the textual proxy for
    "this except/catch clause reacts to the exception" (re-raises, logs,
    or returns an error value) rather than silently swallowing it."""
    for r in func.raises:
        if abs(r.line - catch.line) <= _ADJACENCY_WINDOW:
            return True
    for call in func.calls:
        if _is_log_call(call) and abs(call.line - catch.line) <= _ADJACENCY_WINDOW:
            return True
    for ret in func.returns:
        if abs(ret.line - catch.line) <= _ADJACENCY_WINDOW:
            return True
    return False


# frob:doc docs/modules/arch.md#fallibility-checks
# frob:tests tests/unit/test_arch.py::TestSwallowedException.test_bare_except_with_no_reaction_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestSwallowedException.test_except_with_nearby_log_call_not_flagged  # noqa: E501
def check_swallowed_exception(module: NormalizedModule) -> list[ArchSuggestion]:
    """Swallowed exception (T-0623): flag a bare `except:`/`catch (...)`
    or an `except Exception:` clause (`exception_type` is `None` or
    `"Exception"`) with no raise/log-call/return within
    `_ADJACENCY_WINDOW` lines (`_catch_does_something`) -- an exception
    caught and neither re-raised, logged, nor turned into an error return
    value is silently swallowed. Written once against `NormalizedModule`,
    so it fires for every `LanguageAdapter`."""
    out: list[ArchSuggestion] = []

    def _scan(func: NormalizedFunction, qualname: str) -> None:
        for c in func.catches:
            if c.exception_type not in (None, "Exception"):
                continue
            if _catch_does_something(func, c):
                continue
            caught = c.exception_type or "(bare)"
            out.append(
                ArchSuggestion(
                    file=module.path,
                    line=c.line,
                    category="swallowed-exception",
                    severity="warning",
                    message=(
                        f"`{qualname}` catches `{caught}` and does nothing with it"
                    ),
                    detail=(
                        "a caught exception with no re-raise, log call, or"
                        " error return nearby is silently swallowed --"
                        " re-raise, log, or return an explicit error value"
                    ),
                    symref=qualname,
                )
            )

    for f in module.functions:
        _scan(f, f.name)
    for c in module.classes:
        for m in c.methods:
            _scan(m, _qualname(module, c, m))
    return out


# ---------------------------------------------------------------------------
# recoverable-error-wrong-signature (T-0623)
# ---------------------------------------------------------------------------


# frob:doc docs/modules/arch.md#fallibility-checks
# frob:tests tests/unit/test_arch.py::TestRecoverableErrorWrongSignature.test_raises_value_error_without_result_signature_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestRecoverableErrorWrongSignature.test_raises_value_error_with_result_signature_not_flagged  # noqa: E501
def check_recoverable_error_wrong_signature(
    module: NormalizedModule,
) -> list[ArchSuggestion]:
    """Recoverable-error-wrong-signature (T-0623): flag a function/method
    that `raises` a clearly-recoverable exception type
    (`_RECOVERABLE_EXCEPTION_TYPES`: `ValueError`/`KeyError`/
    `LookupError`/`TypeError`) while its own declared `return_type` does
    NOT contain `"Result["` -- a recoverable, expected failure mode
    (bad user input, a missing key) modeled as a raised exception instead
    of a typed `Result[T, E]` return forces every caller into
    try/except instead of a typani `Result`. A function with no declared
    `return_type` at all is not flagged (nothing to compare against).
    Written once against `NormalizedModule`, so it fires for every
    `LanguageAdapter`."""
    out: list[ArchSuggestion] = []

    def _scan(func: NormalizedFunction, qualname: str) -> None:
        if func.return_type is None or "Result[" in func.return_type:
            return
        recoverable = {
            r.exception_type
            for r in func.raises
            if r.exception_type in _RECOVERABLE_EXCEPTION_TYPES
        }
        if not recoverable:
            return
        out.append(
            ArchSuggestion(
                file=module.path,
                line=func.line,
                category="recoverable-error-wrong-signature",
                severity="suggestion",
                message=(
                    f"`{qualname}` raises {sorted(recoverable)} but returns"
                    f" `{func.return_type}`, not a Result"
                ),
                detail=(
                    "a recoverable/expected error raised instead of"
                    " returned forces every caller into try/except --"
                    " change the signature to return"
                    " Result[T, E] and return the error as a value"
                ),
                symref=qualname,
            )
        )

    for f in module.functions:
        _scan(f, f.name)
    for c in module.classes:
        for m in c.methods:
            _scan(m, _qualname(module, c, m))
    return out


# ---------------------------------------------------------------------------
# over-broad except / re-raise-losing-context (T-0623)
# ---------------------------------------------------------------------------


# frob:doc docs/modules/arch.md#fallibility-checks
# frob:ticket T-0972
# frob:tests tests/unit/test_arch.py::TestOverBroadExcept.test_bare_except_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestOverBroadExcept.test_specific_except_not_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestOverBroadExcept.test_reraise_with_different_type_loses_context_flagged  # noqa: E501
# frob:waive ARCH001 reason="one closure (_scan) walking every catch clause and, per catch, emitting both the bare-except finding and the adjacent-lost-context finding off the same c/qualname locals; splitting the two emits into separate helpers would require passing c, qualname, module, and out across a new boundary for two three-line append blocks that already share the same loop variable"  # noqa: E501
def check_over_broad_except(module: NormalizedModule) -> list[ArchSuggestion]:
    """Over-broad except / re-raise-losing-context (T-0623, one category
    per this ticket's own body text presenting both as a single bullet):
    flags (a) a bare `except:`/`catch (...)` or `except Exception:`
    clause (`exception_type` is `None` or `"Exception"`) -- catching more
    than the call site can name -- and (b) a raise within
    `_ADJACENCY_WINDOW` lines of ANY catch clause whose `exception_type`
    DIFFERS from the catch's own caught type -- a new exception replacing
    the original without `raise ... from e` loses the original traceback/
    cause chain (this model has no `from`-clause field to confirm chaining
    was omitted, so this is the same disclosed best-effort adjacency proxy
    every check in this module uses, not a syntactic certainty). Written
    once against `NormalizedModule`, so it fires for every
    `LanguageAdapter`."""
    out: list[ArchSuggestion] = []

    def _scan(func: NormalizedFunction, qualname: str) -> None:
        for c in func.catches:
            if c.exception_type in (None, "Exception"):
                caught = c.exception_type or "(bare)"
                out.append(
                    ArchSuggestion(
                        file=module.path,
                        line=c.line,
                        category="over-broad-except",
                        severity="suggestion",
                        message=f"`{qualname}` catches `{caught}` -- over-broad",
                        detail=(
                            "a bare except/except Exception catches more"
                            " than the call site can name -- catch the"
                            " specific exception type(s) the call can"
                            " actually raise"
                        ),
                        symref=qualname,
                    )
                )
            for r in func.raises:
                if abs(r.line - c.line) > _ADJACENCY_WINDOW:
                    continue
                if r.exception_type is None or r.exception_type == c.exception_type:
                    continue
                out.append(
                    ArchSuggestion(
                        file=module.path,
                        line=r.line,
                        category="over-broad-except",
                        severity="suggestion",
                        message=(
                            f"`{qualname}` re-raises `{r.exception_type}` from a"
                            f" caught `{c.exception_type or '(bare)'}`, possibly"
                            " losing context"
                        ),
                        detail=(
                            "re-raising a different exception type without"
                            " chaining (`raise ... from e`) loses the"
                            " original traceback/cause -- chain explicitly"
                            " if this is intentional"
                        ),
                        symref=qualname,
                    )
                )

    for f in module.functions:
        _scan(f, f.name)
    for c in module.classes:
        for m in c.methods:
            _scan(m, _qualname(module, c, m))
    return out


# frob:doc docs/modules/arch.md#fallibility-checks
# frob:tests tests/unit/test_arch.py::TestRunFallibilityChecks.test_combines_all_four_checks  # noqa: E501
def run_fallibility_checks(module: NormalizedModule) -> list[ArchSuggestion]:
    """Run every ARCH1xx fallibility check (T-0623:
    `check_unhandled_result`, `check_swallowed_exception`,
    `check_recoverable_error_wrong_signature`, `check_over_broad_except`)
    against one `NormalizedModule` and return the combined suggestions,
    mirroring `frob.arch._logging_checks.run_logging_checks`'s
    convention."""
    out: list[ArchSuggestion] = []
    out.extend(check_unhandled_result(module))
    out.extend(check_swallowed_exception(module))
    out.extend(check_recoverable_error_wrong_signature(module))
    out.extend(check_over_broad_except(module))
    return out

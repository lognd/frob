"""Logging-discipline checks (ARCH1xx, T-0622, EPIC T-0330's observability
family): unlogged error path, unlogged boundary, print-as-diagnostic.

WHY here, not `_solid.py`/`_typedesign.py`: this is its own family in the
epic's catalog (a proxy for "does the code SAY anything when it fails or
crosses a boundary", not a SOLID/type-design concern), so it gets its own
module -- the sibling-module-per-family convention `_solid.py`/
`_layering.py`/`_typedesign.py` already established. Every check here is
written once against `frob.arch._normalized.NormalizedModule` (T-0609),
same convention as those siblings -- nothing here parses a
`tree_sitter.Tree` directly.

STRATA BOUNDARY NOTE (per CLAUDE.md): these checks are logging-IN-CODE
only -- "does a log call exist textually near this error path/boundary" --
with no runtime/flow correlation. Whether a log statement actually FIRES
on the path that needs it, whether it correlates across a distributed
call, and whether the log volume/level is appropriate at runtime are
`frob.strata`'s observability-of-flow concern (circuit breakers, retries,
fallback -- `frob.strata._circuit_breaker`/`_retry`/`_fallback`), not
this module's. A function can pass every check here and still be silently
unobservable at runtime if the log call is unreachable dead code; these
checks only prove a log call is textually present, not that it executes.

SCOPE NOTE: `src/frob/arch/_models.py`'s scope lease was free at
implementation time (unlike T-0621's), so the three categories below
extend the SHARED `frob.arch._models.ArchCategory`/`ArchSuggestion`
directly rather than introducing a local pair -- no fold-in follow-up
needed for this ticket.
"""
# frob:waive INV006 reason="this module's 'only' occurrences are source-level \
# design-rationale prose (the module docstring's strata-boundary note and the \
# per-heuristic helper docstrings describing what already-implemented text \
# matching does), verifiable by reading the function it annotates, not a \
# separate cross-module contract needing its own tracked invariant -- the \
# same INV006 first-turn-on-pool disposition frob.arch._solid/_typedesign's \
# own module docstrings already carry"

from __future__ import annotations

from frob.arch._models import ArchSuggestion
from frob.arch._normalized import (
    NormalizedCall,
    NormalizedClass,
    NormalizedFunction,
    NormalizedModule,
)

#: Callee substrings (T-0622) counted as "this call is a log statement" --
#: a bare-text heuristic over `NormalizedCall.callee`'s dotted form
#: (`logger.info`, `self._log.warning`, `logging.error`, ...), not a
#: resolved-symbol match (this model does not resolve imports to their
#: origin), matching every other heuristic-over-callee-text detector in
#: this package (`frob.arch._concurrency`'s fork/pool detectors).
_LOG_CALLEE_MARKERS = ("log.", "logger.", "logging.", "_log.", "_logger.")

#: `print` calls inside a module whose repo-relative path contains one of
#: these substrings are NOT flagged by `check_print_as_diagnostic` (T-0622)
#: -- a CLI-output module's whole job is writing to stdout, so `print` is
#: the correct call there, not a diagnostic-logging gap.
_CLI_OUTPUT_PATH_MARKERS = ("cli", "__main__", "console")

#: Callee substrings (T-0622) counted as a "boundary" call site --
#: subprocess/network/filesystem operations whose failure is invisible to
#: an operator unless something nearby logs it. Bare-text heuristic over
#: `NormalizedCall.callee`, same convention as `_LOG_CALLEE_MARKERS`.
_BOUNDARY_CALLEE_MARKERS = (
    "subprocess.",
    "os.system",
    "os.popen",
    "requests.",
    "httpx.",
    "urllib.",
    "socket.",
    "open(",
    "os.remove",
    "os.unlink",
    "os.mkdir",
    "os.makedirs",
    "os.rmdir",
    "shutil.",
)

#: Line-adjacency window (T-0622) a log call must fall within, relative to
#: the error-path/boundary line it is meant to cover, to count as "inside
#: it" -- the same style of textual proxy `frob.arch._solid`'s guard-
#: clause detectors use for raise-adjacent-to-branch, since this model has
#: no block-scoping finer than a whole function body.
_LOG_ADJACENCY_WINDOW = 3


def _qualname(
    module: NormalizedModule, cls: NormalizedClass | None, func: NormalizedFunction
) -> str:
    """`path::Class.method`/`path::function` symref (T-0289's shape,
    T-0622) for `func`, optionally scoped to `cls`."""
    if cls is None:
        return f"{module.path}::{func.name}"
    return f"{module.path}::{cls.name}.{func.name}"


def _is_log_call(call: NormalizedCall) -> bool:
    """True when `call`'s callee text looks like a log statement
    (`_LOG_CALLEE_MARKERS`, T-0622) -- a bare-text heuristic, not a
    resolved-symbol match."""
    callee = call.callee.lower()
    return any(marker in callee for marker in _LOG_CALLEE_MARKERS)


def _is_print_call(call: NormalizedCall) -> bool:
    """True when `call`'s callee is exactly `print` (T-0622) -- a bare
    `print` identifier, not a dotted `obj.print` attribute call."""
    return call.callee == "print"


def _is_boundary_call(call: NormalizedCall) -> bool:
    """True when `call`'s callee text looks like a subprocess/network/
    filesystem operation (`_BOUNDARY_CALLEE_MARKERS`, T-0622) -- a
    bare-text heuristic, not a resolved-symbol match."""
    return any(marker in call.callee for marker in _BOUNDARY_CALLEE_MARKERS)


def _has_nearby_log_call(calls: list[NormalizedCall], line: int) -> bool:
    """True when some call in `calls` is both a log call (`_is_log_call`)
    and within `_LOG_ADJACENCY_WINDOW` source lines of `line` (T-0622) --
    the function-body-wide log-call list is the same one every check in
    this module scans, only the adjacency window differs per call site."""
    return any(
        _is_log_call(c) and abs(c.line - line) <= _LOG_ADJACENCY_WINDOW for c in calls
    )


# ---------------------------------------------------------------------------
# unlogged error path (T-0622)
# ---------------------------------------------------------------------------


# frob:doc docs/modules/arch.md#logging-discipline-checks
# frob:tests tests/unit/test_arch.py::TestUnloggedErrorPath.test_catch_with_no_nearby_log_call_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestUnloggedErrorPath.test_catch_with_nearby_log_call_not_flagged  # noqa: E501
def check_unlogged_error_path(module: NormalizedModule) -> list[ArchSuggestion]:
    """Unlogged error path (T-0622): flag an `except`/`catch` clause
    (`NormalizedFunction.catches`) or a `return`-of-`Err(...)` statement
    (`NormalizedFunction.returns` whose `value_text` contains `"Err("`,
    typani's Result-error-value convention) with no log call
    (`_has_nearby_log_call`) within `_LOG_ADJACENCY_WINDOW` lines -- an
    error path a caller/operator has no textual evidence ever fired.
    Written once against `NormalizedModule`, so it fires for every
    `LanguageAdapter`."""
    out: list[ArchSuggestion] = []

    def _scan(func: NormalizedFunction, qualname: str) -> None:
        for c in func.catches:
            if _has_nearby_log_call(func.calls, c.line):
                continue
            caught = c.exception_type or "exception"
            out.append(
                ArchSuggestion(
                    file=module.path,
                    line=c.line,
                    category="unlogged-error-path",
                    severity="suggestion",
                    message=f"`{qualname}` catches `{caught}` with no nearby log call",
                    detail=(
                        "an except/catch clause with no log statement inside"
                        " it leaves no textual evidence the error path ever"
                        " fired -- log the exception before handling it"
                    ),
                    symref=qualname,
                )
            )
        for r in func.returns:
            if r.value_text is None or "Err(" not in r.value_text:
                continue
            if _has_nearby_log_call(func.calls, r.line):
                continue
            out.append(
                ArchSuggestion(
                    file=module.path,
                    line=r.line,
                    category="unlogged-error-path",
                    severity="suggestion",
                    message=f"`{qualname}` returns an Err with no nearby log call",
                    detail=(
                        "a `return Err(...)` with no log statement nearby"
                        " leaves no textual evidence the error path ever"
                        " fired -- log before returning the error value"
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
# unlogged boundary (T-0622)
# ---------------------------------------------------------------------------


# frob:doc docs/modules/arch.md#logging-discipline-checks
# frob:tests tests/unit/test_arch.py::TestUnloggedBoundary.test_public_entry_point_with_no_log_call_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestUnloggedBoundary.test_boundary_call_with_no_nearby_log_call_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestUnloggedBoundary.test_private_function_not_flagged  # noqa: E501
def check_unlogged_boundary(module: NormalizedModule) -> list[ArchSuggestion]:
    """Unlogged boundary (T-0622): flag (a) a PUBLIC function/method (name
    not starting with `_`) whose own body has no log call anywhere
    (`_is_log_call`), or (b) a subprocess/network/filesystem call site
    (`_is_boundary_call`) with no log call (`_has_nearby_log_call`) within
    `_LOG_ADJACENCY_WINDOW` lines -- a public entry point or an I/O
    boundary with nothing logging its own invocation/outcome is invisible
    to an operator diagnosing a failure. Written once against
    `NormalizedModule`, so it fires for every `LanguageAdapter`."""
    out: list[ArchSuggestion] = []

    def _scan(func: NormalizedFunction, qualname: str, bare_name: str) -> None:
        if bare_name.startswith("_"):
            return
        if not any(_is_log_call(c) for c in func.calls):
            out.append(
                ArchSuggestion(
                    file=module.path,
                    line=func.line,
                    category="unlogged-boundary",
                    severity="suggestion",
                    message=f"`{qualname}` is a public entry point with no log call",
                    detail=(
                        "a public function/method with no log statement"
                        " anywhere in its body gives an operator no"
                        " textual evidence it was ever invoked"
                    ),
                    symref=qualname,
                )
            )
        for call in func.calls:
            if not _is_boundary_call(call):
                continue
            if _has_nearby_log_call(func.calls, call.line):
                continue
            out.append(
                ArchSuggestion(
                    file=module.path,
                    line=call.line,
                    category="unlogged-boundary",
                    severity="suggestion",
                    message=(
                        f"`{qualname}` calls `{call.callee}` with no nearby log call"
                    ),
                    detail=(
                        "a subprocess/network/filesystem call site with no"
                        " log statement nearby leaves no textual evidence"
                        " of the boundary crossing or its outcome"
                    ),
                    symref=qualname,
                )
            )

    for f in module.functions:
        _scan(f, f.name, f.name)
    for c in module.classes:
        for m in c.methods:
            _scan(m, _qualname(module, c, m), m.name)
    return out


# ---------------------------------------------------------------------------
# print-as-diagnostic (T-0622)
# ---------------------------------------------------------------------------


# frob:doc docs/modules/arch.md#logging-discipline-checks
# frob:tests tests/unit/test_arch.py::TestPrintAsDiagnostic.test_print_call_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestPrintAsDiagnostic.test_print_call_in_cli_module_not_flagged  # noqa: E501
def check_print_as_diagnostic(module: NormalizedModule) -> list[ArchSuggestion]:
    """Print-as-diagnostic (T-0622): flag a `print(...)` call
    (`_is_print_call`) in a module whose repo-relative path is NOT a
    CLI-output module (`_CLI_OUTPUT_PATH_MARKERS`) -- `print` used where a
    module logger call is expected produces output with no level, no
    logger name, and nothing a log aggregator can filter on. A CLI-output
    module's whole job is writing to stdout, so `print` there is correct
    and not flagged. Written once against `NormalizedModule`, so it fires
    for every `LanguageAdapter`."""
    out: list[ArchSuggestion] = []
    path_lower = module.path.lower()
    if any(marker in path_lower for marker in _CLI_OUTPUT_PATH_MARKERS):
        return out

    def _scan(func: NormalizedFunction, qualname: str) -> None:
        for call in func.calls:
            if not _is_print_call(call):
                continue
            out.append(
                ArchSuggestion(
                    file=module.path,
                    line=call.line,
                    category="print-as-diagnostic",
                    severity="suggestion",
                    message=(
                        f"`{qualname}` calls `print()` where a log call is expected"
                    ),
                    detail=(
                        "print() has no level, no logger name, and cannot"
                        " be filtered by a log aggregator -- use the"
                        " module logger instead, outside a CLI-output"
                        " module"
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


# frob:doc docs/modules/arch.md#logging-discipline-checks
# frob:tests tests/unit/test_arch.py::TestRunLoggingChecks.test_combines_all_three_checks  # noqa: E501
def run_logging_checks(module: NormalizedModule) -> list[ArchSuggestion]:
    """Run every ARCH1xx logging-discipline check (T-0622:
    `check_unlogged_error_path`, `check_unlogged_boundary`,
    `check_print_as_diagnostic`) against one `NormalizedModule` and
    return the combined suggestions, mirroring
    `frob.arch._typedesign.run_typedesign_checks`'s convention."""
    out: list[ArchSuggestion] = []
    out.extend(check_unlogged_error_path(module))
    out.extend(check_unlogged_boundary(module))
    out.extend(check_print_as_diagnostic(module))
    return out

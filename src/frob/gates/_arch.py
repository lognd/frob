"""ARCH001: complexity-aware long-function findings, channeled through the
gate/waiver path (docs/modules/gates.md#rule-catalog, T-0289).

T-0101's original decision kept `frob.arch`'s whole suggestion surface
outside the `Violation`/`frob:waive` pipeline (`frob.gates._unwaivable_channel_rules`'s
docstring) -- reasonable at the time, since `ArchSuggestion`s carried no
symbol identity a waiver could bind to precisely. T-0289 revisits exactly
one category, long-function, now that `frob.arch._python`/`_cpp` set
`symref`/`metric` on every long-function finding: a long-AND-complex
function residue is real technical debt that deserves the same reasoned,
auditable, at-the-code waiver every other rule gets (`frob:waive ARCH001
reason="..." [ceiling=N]`), not a silent "the tool doesn't listen here"
carve-out. Every OTHER arch category (god-class, high-coupling, deep-
nesting, abstraction-opportunity, large-file) stays exactly as T-0101 left
it -- unwaivable-channel WARN-only suggestions, not gate violations. Do not
widen this module to cover them without a fresh design decision.
"""

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

#: The one `frob.arch` category this gate channels into `Violation`s.
_ARCH_LONG_FUNCTION_CATEGORY = "long-function"


# frob:doc docs/modules/gates.md#rule-catalog
# frob:enforces ACC-2-1-LONG-FUNCTION
# frob:enforces CHK-GATE-ARCH001
def arch_gate(root: Path) -> tuple[Violation, ...]:
    """ARCH001: one `Violation` per long-AND-complex python/C++ function
    `frob.arch.analyze_project` still flags after its complexity filter
    (`frob.arch._python._py_is_complex` / `_cpp._cpp_is_complex`) --
    `symref`/`metric` carried through so `frob.gates._match_waiver` can bind
    a `frob:waive ARCH001 reason="..." [ceiling=N]` to the exact function.

    T-0373: thresholds come from `frob.app.config.load_arch_config` (the
    repo's `[arch]` `frob.toml` table, calibrated-default fallback) instead
    of `analyze_project`'s own conservative keyword defaults -- the gate
    used to silently ignore the user's disclosed 60/800 calibration."""
    from frob.app.config import load_arch_config
    from frob.arch import analyze_project

    result = analyze_project(root, **load_arch_config(root))
    violations: list[Violation] = []
    for s in result.suggestions:
        if s.category != _ARCH_LONG_FUNCTION_CATEGORY:
            continue
        violations.append(
            Violation(
                rule="ARCH001",
                severity=Severity.WARN,
                file=s.file,
                line=s.line or 0,
                message=f"ARCH001: {s.message}",
                symref=s.symref,
                metric=s.metric,
            )
        )
    _log.info("arch_gate: %d ARCH001 violation(s)", len(violations))
    return tuple(violations)


__all__ = ["arch_gate"]

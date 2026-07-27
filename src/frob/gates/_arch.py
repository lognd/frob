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
carve-out. Every OTHER arch category not listed below stays exactly as
T-0101 left it -- unwaivable-channel WARN-only suggestions, not gate
violations. Do not widen this module further without a fresh design
decision.

T-0728 is that fresh design decision for exactly three more categories:
`low-cohesion-class` (ARCH101), `god-module` (ARCH102), and
`mixed-concern-function` (ARCH103) -- T-0616's ARCH1xx SRP/cohesion family
(`frob.arch._srp`), each already carrying `symref` a waiver can bind to,
same shape as `long-function`. T-0616 built the checks but left them
un-dispatched by `analyze_project` and un-registered here (its Done
report's disclosed follow-up); this closes that catalogued-is-not-enforced
gap. All three channel at `Severity.WARN`, matching ARCH001 -- none of the
three has been observed to fire against this repo's own current source at
their calibrated `frob.app.config.load_arch_config` defaults (T-0728 Done
report), so WARN-not-ERROR is a plain precedent match, not a softening
made just to land quietly.

T-1034 is the next such fresh design decision, for exactly one more
category: `cpp-noexcept-throws` (CPPTHROW001, T-0687's C++ may-throw
analysis, `frob.arch._cpp_mayraise`). Unlike every category above, this
one channels at `Severity.ERROR`, not `Severity.WARN` -- an escaping
exception from a C++ `noexcept` function is `std::terminate` at runtime,
not a style preference a team can defer; `ArchSuggestion.severity` is
already `"error"` for this category (T-0687 added that `ArchSeverity`
value specifically for it, see `frob.arch._models`'s own module-level
comment), so this gate reads that severity through rather than
hardcoding `Severity.WARN` the way every prior category here does. A real
run against this repo's own source at landing time surfaced zero
findings (no `noexcept` function in this repo's own C++ test fixtures
reaches a may-throw call) -- there is no pre-existing debt corpus an
ERROR severity would instantly red, so ERROR ships directly, not deferred
behind a WARN-first promotion the way EXHAUST001/002 (T-0688) needed for
their own 176-finding first run.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/gates/_arch.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

#: The `frob.arch` categories this gate channels into `Violation`s: the
#: original T-0289 long-function category plus (T-0728) T-0616's ARCH1xx
#: SRP/cohesion family, each mapped to its rule id.
_ARCH_LONG_FUNCTION_CATEGORY = "long-function"
_ARCH_CATEGORY_TO_RULE = {
    _ARCH_LONG_FUNCTION_CATEGORY: "ARCH001",
    "low-cohesion-class": "ARCH101",
    "god-module": "ARCH102",
    "mixed-concern-function": "ARCH103",
    # T-1034: cpp-noexcept-throws (frob.arch._cpp_mayraise, T-0687) --
    # see this module's own docstring for why this one category channels
    # at Severity.ERROR, not Severity.WARN like every category above.
    "cpp-noexcept-throws": "CPPTHROW001",
}

#: Categories (T-1034) whose `Violation` uses `Severity.ERROR` instead of
#: the `Severity.WARN` every prior `_ARCH_CATEGORY_TO_RULE` entry hardcodes
#: -- a `noexcept` hard-boundary violation is std::terminate at runtime,
#: not deferrable debt. Read as an allowlist (not the reverse) so a future
#: category added to `_ARCH_CATEGORY_TO_RULE` defaults to the existing
#: WARN precedent unless explicitly opted into ERROR here.
_ERROR_SEVERITY_CATEGORIES = frozenset({"cpp-noexcept-throws"})


# frob:doc docs/modules/gates.md#rule-catalog
# frob:enforces ACC-2-1-LONG-FUNCTION
# frob:enforces CHK-GATE-ARCH001
# T-1020-followup: T-0728 disclosed CHK-GATE-ARCH101/102/103 as a land
# obligation left for a later pass -- this closes it, same
# `_ARCH_CATEGORY_TO_RULE` sites ARCH001 already binds to.
# frob:enforces CHK-GATE-ARCH101
# frob:enforces CHK-GATE-ARCH102
# frob:enforces CHK-GATE-ARCH103
# frob:enforces CHK-GATE-CPPTHROW001
# frob:tests tests/unit/test_arch_srp.py::TestArchGateSrpWiring.test_two_cluster_class_fires_arch101  # noqa: E501
# frob:tests tests/unit/test_arch_srp.py::TestArchGateSrpWiring.test_cohesive_class_does_not_fire_arch101  # noqa: E501
# frob:tests tests/unit/test_arch_srp.py::TestArchGateSrpWiring.test_god_module_fires_arch102  # noqa: E501
# frob:tests tests/unit/test_arch_srp.py::TestArchGateSrpWiring.test_mixed_concern_function_fires_arch103  # noqa: E501
# frob:tests tests/unit/test_arch_srp.py::TestArchGateSrpWiring.test_arch101_respects_explicit_frob_toml_override  # noqa: E501
# frob:tests tests/test_arch_gate.py::TestArchGateCppThrow.test_noexcept_may_throw_fires_cppthrow001_error  # noqa: E501
# frob:tests tests/test_arch_gate.py::TestArchGateCppThrow.test_noexcept_with_catch_all_does_not_fire_cppthrow001  # noqa: E501
def arch_gate(root: Path) -> tuple[Violation, ...]:
    """ARCH001: one `Violation` per long-AND-complex python/C++ function
    `frob.arch.analyze_project` still flags after its complexity filter
    (`frob.arch._python._py_is_complex` / `_cpp._cpp_is_complex`).
    T-0728 adds ARCH101 (`low-cohesion-class`), ARCH102 (`god-module`), and
    ARCH103 (`mixed-concern-function`) -- T-0616's ARCH1xx SRP/cohesion
    family, now dispatched by `analyze_project` itself
    (`frob.arch._run_srp_checks_python`). T-1034 adds CPPTHROW001
    (`cpp-noexcept-throws`, T-0687's C++ may-throw analysis,
    `frob.arch._cpp_mayraise`) -- see this module's own docstring for why
    THIS rule channels at `Severity.ERROR`, every other rule here at
    `Severity.WARN`. Every rule's `symref`/`metric` carried through so
    `frob.gates._match_waiver` can bind a `frob:waive ARCHxxx
    reason="..." [ceiling=N]` to the exact symbol.

    T-0373: thresholds come from `frob.app.config.load_arch_config` (the
    repo's `[arch]` `frob.toml` table, calibrated-default fallback) instead
    of `analyze_project`'s own conservative keyword defaults -- the gate
    used to silently ignore the user's disclosed 60/800 calibration. T-0728
    extends the same threading to its own five ARCH1xx knobs."""
    from frob.app.config import load_arch_config
    from frob.arch import analyze_project

    result = analyze_project(root, **load_arch_config(root))
    violations: list[Violation] = []
    for s in result.suggestions:
        rule = _ARCH_CATEGORY_TO_RULE.get(s.category)
        if rule is None:
            continue
        severity = (
            Severity.ERROR
            if s.category in _ERROR_SEVERITY_CATEGORIES
            else Severity.WARN
        )
        violations.append(
            Violation(
                rule=rule,
                severity=severity,
                file=s.file,
                line=s.line or 0,
                message=f"{rule}: {s.message}",
                symref=s.symref,
                metric=s.metric,
            )
        )
    _log.info("arch_gate: %d arch-family violation(s)", len(violations))
    return tuple(violations)


__all__ = ["arch_gate"]

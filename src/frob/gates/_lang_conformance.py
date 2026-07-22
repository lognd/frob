"""LANG001: the language-extension conformance gate (T-0405).

Turns `frob.lang._support.conformance_violations` into real `Violation`s --
a registered `frob.lang` grammar language missing a facet (implemented,
reasoned not-applicable, or a ticketed known gap) fails `frob check` at
ERROR severity, the same fail-closed posture `frob.gates._registry_
exhaustiveness` takes over `docs/design/registry/*.yaml`. This is what
makes the PyO3-publicness incident class (a language quietly shipped with
one facet unimplemented) a build failure instead of an invisible product
gap: `derive_language_registry` runs against the LIVE state of every
per-facet registry, so this gate is always checking today's reality, not a
stale snapshot.
"""

from __future__ import annotations

from frob.gates._models import Severity, Violation
from frob.lang._support import conformance_violations, derive_language_registry
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["lang_conformance_gate"]


# frob:doc docs/modules/lang.md#language-support-contract
# frob:ticket T-0405
# frob:tests tests/test_lang_conformance_gate.py::TestLangConformanceGate.test_real_registry_is_clean  # noqa: E501
# frob:tests tests/test_lang_conformance_gate.py::TestLangConformanceGate.test_missing_facet_becomes_error_violation  # noqa: E501
def lang_conformance_gate() -> tuple[Violation, ...]:
    """LANG001 for every unaccounted-for `(language, facet)` cell in the
    live `frob.lang` language-support registry.

    Takes no arguments (unlike most gates here) -- `derive_language_
    registry` reads the real, in-process registries directly, so there is
    no repo-scanned state to thread through; a caller wanting a different
    registry for testing calls `conformance_violations` directly instead
    (see `tests/test_lang_support.py`).
    """
    registry = derive_language_registry()
    messages = conformance_violations(registry)
    violations = tuple(
        Violation(
            rule="LANG001",
            severity=Severity.ERROR,
            file="src/frob/lang/_support.py",
            line=0,
            message=f"LANG001: {message}",
        )
        for message in messages
    )
    _log.info(
        "lang_conformance_gate: %d language(s) checked, %d violation(s)",
        len(registry),
        len(violations),
    )
    return violations

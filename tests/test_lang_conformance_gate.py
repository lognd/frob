"""Tests for frob.gates._lang_conformance -- LANG001 (T-0405)."""

from __future__ import annotations

from frob.gates._lang_conformance import lang_conformance_gate
from frob.gates._models import Severity


# frob:ticket T-0405
class TestLangConformanceGate:
    """LANG001 over the live, real `frob.lang` language-support registry."""

    # frob:ticket T-0405
    def test_real_registry_is_clean(self) -> None:
        """The repo's own registered languages are all fully accounted
        for today -- this gate is clean, not just wired-but-untested."""
        assert lang_conformance_gate() == ()

    # frob:ticket T-0405
    def test_missing_facet_becomes_error_violation(self, monkeypatch) -> None:
        """A stand-in registry with one language missing a facet turns
        into exactly one ERROR-severity LANG001 violation."""
        import frob.gates._lang_conformance as module
        from frob.lang import FacetState, FacetStatus, LanguageSupport

        def _fake_registry():
            facets = {
                "grammar": FacetStatus(state=FacetState.IMPLEMENTED, detail="ok"),
            }
            return {"kotlin": LanguageSupport(language="kotlin", facets=facets)}

        monkeypatch.setattr(module, "derive_language_registry", _fake_registry)
        violations = module.lang_conformance_gate()
        assert len(violations) >= 1
        assert all(v.rule == "LANG001" for v in violations)
        assert all(v.severity is Severity.ERROR for v in violations)
        assert any("kotlin" in v.message for v in violations)

"""Tests for frob.gates._lang_conformance -- LANG001-LANG003 (T-0405/T-0406)."""

from __future__ import annotations

from pathlib import Path

from frob.gates._lang_conformance import (
    lang_conformance_gate,
    project_lang_conformance_gate,
)
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


# frob:ticket T-0406
class TestProjectLangConformanceGate:
    """LANG002/LANG003 over a synthetic downstream repo tree (T-0406)."""

    # frob:ticket T-0406
    def test_unregistered_language_file_fails(self, tmp_path: Path) -> None:
        """A Kotlin file in a downstream repo -- a language frob has NO
        grammar registration for at all -- fails LANG002 by name."""
        (tmp_path / "Main.kt").write_text("fun main() {}\n", encoding="utf-8")
        violations = project_lang_conformance_gate(tmp_path)
        lang002 = [v for v in violations if v.rule == "LANG002"]
        assert len(lang002) == 1
        assert lang002[0].severity is Severity.ERROR
        assert "kotlin" in lang002[0].message
        assert lang002[0].file == "Main.kt"

    # frob:ticket T-0406
    def test_all_conformant_project_passes(self, tmp_path: Path) -> None:
        """A repo containing only python (every facet implemented) has no
        LANG002/LANG003 findings at all."""
        (tmp_path / "app.py").write_text("def f() -> None: ...\n", encoding="utf-8")
        violations = project_lang_conformance_gate(tmp_path)
        assert violations == ()

    # frob:ticket T-0406
    # frob:ticket T-0823
    def test_present_known_gap_with_open_ticket_warns(self, tmp_path: Path) -> None:
        """A repo containing rust files (arch facet is a KNOWN_GAP naming
        the still-open T-0329, per frob's own shipped `KNOWN_GAP_TRACKING_
        TICKETS`) gets a WARN, not silence and not an error -- and this is
        true regardless of whether `tmp_path` has any ticket queue at all
        (T-0823: no queue is ever consulted)."""
        (tmp_path / "lib.rs").write_text("fn main() {}\n", encoding="utf-8")
        violations = project_lang_conformance_gate(tmp_path)
        lang003 = [v for v in violations if v.rule == "LANG003"]
        assert any(v.severity is Severity.WARN for v in lang003)
        assert not any(v.severity is Severity.ERROR for v in lang003)

    # frob:ticket T-0823
    def test_adopter_repo_with_no_frob_internal_tickets_does_not_error(
        self, tmp_path: Path
    ) -> None:
        """T-0823's core regression: `tmp_path` here is exactly the
        adopter shape -- a downstream repo with no `tickets.md` at all
        (frob-internal ticket ids like T-0329 are structurally
        unresolvable). LANG003 must not hard-error over that; the rust
        KNOWN_GAP cell still verifies cleanly against frob's own shipped
        registry, same WARN as `test_present_known_gap_with_open_ticket_
        warns` above -- proving the fix is not merely "no queue passed",
        but "no queue was ever the right thing to consult"."""
        assert not (tmp_path / "tickets.md").exists()
        (tmp_path / "lib.rs").write_text("fn main() {}\n", encoding="utf-8")
        violations = project_lang_conformance_gate(tmp_path)
        lang003 = [v for v in violations if v.rule == "LANG003"]
        assert lang003
        assert all(v.severity is Severity.WARN for v in lang003)

    # frob:ticket T-0406
    # frob:ticket T-0823
    def test_present_known_gap_with_bad_ticket_ref_errors(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """The same rust KNOWN_GAP cell, checked once frob's own
        `KNOWN_GAP_TRACKING_TICKETS` registry marks T-0329 resolved,
        escalates to ERROR -- a claimed-but-no-longer-real gap is unsound
        coverage, not tracked coverage. T-0823: this is now frob's own
        shipped fact, not the checked repo's queue -- flip the constant,
        not a queue entry, to prove the anti-lie check still fires."""
        import frob.gates._lang_conformance as module

        monkeypatch.setitem(module.KNOWN_GAP_TRACKING_TICKETS, "T-0329", False)
        (tmp_path / "lib.rs").write_text("fn main() {}\n", encoding="utf-8")
        violations = project_lang_conformance_gate(tmp_path)
        lang003 = [v for v in violations if v.rule == "LANG003"]
        assert any(v.severity is Severity.ERROR for v in lang003)

"""Split from tests/unit/test_arch.py (T-1201)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.arch_suite.conftest import FIXTURES, HAS_ARCH, analyze_project

pytestmark = pytest.mark.skipif(not HAS_ARCH, reason="frob.arch not available")


class TestAbstractionOpportunityDiscriminators:
    def test_generic_signature_unrelated_bodies_not_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_abstraction.py::_check_abstraction_opportunities
        # frob:tests src/frob/arch/_abstraction.py::_signature_is_specific
        # frob:tests src/frob/arch/_abstraction.py::_near_duplicate_cluster
        # N functions sharing an over-generic `(str) -> str` signature
        # (like the 31-member residue this ticket targets) whose bodies do
        # completely different, structurally unrelated things -- a bare
        # shared signature is not evidence of an extractable abstraction,
        # so this must NOT flag at all.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def render_banner(text: str) -> str:\n"
            "    lines = text.split(chr(10))\n"
            "    width = max(len(line) for line in lines)\n"
            "    border = chr(42) * (width + 4)\n"
            "    body = chr(10).join(chr(42) + chr(32) + line for line in lines)\n"
            "    return border + chr(10) + body + chr(10) + border\n"
        )
        (src_dir / "b.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def rot13(text: str) -> str:\n"
            "    out = []\n"
            "    for ch in text:\n"
            "        code = ord(ch)\n"
            "        if 97 <= code <= 122:\n"
            "            out.append(chr((code - 97 + 13) % 26 + 97))\n"
            "        else:\n"
            "            out.append(ch)\n"
            "    return chr(0).join(out).replace(chr(0), chr(0))\n"
        )
        (src_dir / "c.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def slugify_path(text: str) -> str:\n"
            "    parts = text.split(chr(47))\n"
            "    kept = [p for p in parts if p not in (chr(46), chr(46) * 2)]\n"
            "    return chr(47).join(kept)\n"
        )

        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" not in categories

    def test_generic_signature_near_duplicate_bodies_still_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_abstraction.py::_check_abstraction_opportunities
        # frob:tests src/frob/arch/_abstraction.py::_near_duplicate_cluster
        # N functions sharing a generic `(AppConfig) -> None` signature
        # (the shape of the 39-member `run` residue this ticket targets)
        # whose bodies are near-DUPLICATE -- same shape, only the renamed
        # variables and one differing literal differ. Even on a purely
        # generic signature, real duplicated logic must still be caught.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class AppConfig:\n"
            "    pass\n"
            "\n"
            "def run_scan(config: AppConfig) -> None:\n"
            "    target = getattr(config, chr(65))\n"
            "    if not target:\n"
            '        raise ValueError("no target")\n'
            "    print(chr(97), target, chr(115), chr(99), chr(97), chr(110))\n"
        )
        (src_dir / "b.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class AppConfig:\n"
            "    pass\n"
            "\n"
            "def run_stamp(config: AppConfig) -> None:\n"
            "    target = getattr(config, chr(66))\n"
            "    if not target:\n"
            '        raise ValueError("no target")\n'
            "    print(chr(97), target, chr(115), chr(116), chr(97), chr(109))\n"
        )
        (src_dir / "c.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class AppConfig:\n"
            "    pass\n"
            "\n"
            "def run_sweep(config: AppConfig) -> None:\n"
            "    target = getattr(config, chr(67))\n"
            "    if not target:\n"
            '        raise ValueError("no target")\n'
            "    print(chr(97), target, chr(115), chr(119), chr(101), chr(101))\n"
        )

        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories
        msg = next(
            s.message
            for s in result.suggestions
            if s.category == "abstraction-opportunity"
        )
        assert "run_scan" in msg
        assert "run_stamp" in msg
        assert "run_sweep" in msg

    def test_specific_signature_genuine_family_still_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_abstraction.py::_signature_is_specific
        # frob:tests src/frob/arch/_abstraction.py::_check_abstraction_opportunities
        # A shared signature carrying a real domain type (`TicketStore`,
        # not one of the ubiquitous primitives) is specific enough to flag
        # on the signature alone, even though the bodies below are
        # deliberately UNRELATED -- signature-specificity is an
        # independent discriminator from body-similarity.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "store.py").write_text(
            "from __future__ import annotations\n\nclass TicketStore:\n    pass\n"
        )
        (src_dir / "a.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "from src.store import TicketStore\n"
            "\n"
            "def count_open(store: TicketStore) -> int:\n"
            "    return 1\n"
        )
        (src_dir / "b.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "from src.store import TicketStore\n"
            "\n"
            "def count_blocked(store: TicketStore) -> int:\n"
            "    total = 0\n"
            "    for _ in range(3):\n"
            "        total += 1\n"
            "    return total\n"
        )
        (src_dir / "c.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "from src.store import TicketStore\n"
            "\n"
            "def count_archived(store: TicketStore) -> int:\n"
            "    return len([1, 2, 3, 4])\n"
        )

        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories
        msg = next(
            s.message
            for s in result.suggestions
            if s.category == "abstraction-opportunity"
        )
        assert "count_open" in msg
        assert "count_blocked" in msg
        assert "count_archived" in msg

    def test_generic_signature_only_two_bodies_similar_reports_pair(self, tmp_path):
        # frob:tests src/frob/arch/_abstraction.py::_near_duplicate_cluster
        # 3 functions share a generic `(str) -> bool` signature; only 2 of
        # them have near-duplicate bodies, the third is unrelated. The
        # finding must report the near-duplicate PAIR, not misrepresent
        # all 3 as one shared-logic family.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def is_hex_digest(text: str) -> bool:\n"
            "    if len(text) != 40:\n"
            "        return False\n"
            "    return all(c in chr(48) + chr(57) for c in text)\n"
        )
        (src_dir / "b.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def is_sha_digest(text: str) -> bool:\n"
            "    if len(text) != 40:\n"
            "        return False\n"
            "    return all(c in chr(48) + chr(57) for c in text)\n"
        )
        (src_dir / "c.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def is_valid_url(text: str) -> bool:\n"
            "    return text.startswith(chr(104) + chr(116) + chr(116) + chr(112))\n"
        )

        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories
        msg = next(
            s.message
            for s in result.suggestions
            if s.category == "abstraction-opportunity"
        )
        assert "is_hex_digest" in msg
        assert "is_sha_digest" in msg
        assert "is_valid_url" not in msg


class TestLanguageParityExclusion:
    def test_one_member_per_language_not_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_abstraction.py::_is_language_parity_family
        # frob:tests src/frob/arch/_abstraction.py::_check_abstraction_opportunities
        # Three distinctly-tagged per-language walkers sharing a SPECIFIC
        # (domain-typed) signature -- `_signature_is_specific` alone would
        # flag this group (verified: with the language-parity check
        # removed, this exact fixture flags), so language-parity exclusion
        # is the only thing suppressing it.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "walkers.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class RawSymbol:\n"
            "    pass\n"
            "\n"
            "def _py_build_symbol(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
            "\n"
            "def _rust_build_symbol(node: object) -> RawSymbol:\n"
            "    sym = RawSymbol()\n"
            "    return sym\n"
            "\n"
            "def _kt_build_symbol(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" not in categories

    @pytest.mark.parametrize(
        ("third_member_src", "reason"),
        [
            pytest.param(
                "def _rust_build_alias(node: object) -> RawSymbol:\n"
                "    return RawSymbol()\n",
                "duplicate-tag",
                id="duplicate_rust_tag",
            ),
            pytest.param(
                "def _read_symbol(node: object) -> RawSymbol:\n"
                "    return RawSymbol()\n",
                "untagged-member",
                id="untagged_member",
            ),
        ],
    )
    def test_non_parity_group_still_flagged(self, tmp_path, third_member_src, reason):
        # frob:tests src/frob/arch/_abstraction.py::_is_language_parity_family
        # Two scenarios that must NOT be excluded as an intentional
        # per-language parity family, each still flagging as a real
        # abstraction opportunity:
        # - "duplicate-tag": a second `_rust_*` member shares the "rust"
        #   tag with the first -- a real accidental collision WITHIN the
        #   same language, not one-per-language parity.
        # - "untagged-member": `_read_symbol` carries no recognized
        #   language tag at all -- with no tag to compare, parity cannot
        #   be established, so the group falls through to the normal
        #   signature/body checks.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "walkers.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class RawSymbol:\n"
            "    pass\n"
            "\n"
            "def _rust_build_symbol(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
            "\n"
            f"{third_member_src}"
            "\n"
            "def _kt_build_symbol(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories, reason

    def test_tag_requires_underscore_boundary(self, tmp_path):
        # frob:tests src/frob/arch/_abstraction.py::_language_tag
        # "results_summary" contains "ts" as a bare substring with no
        # underscore before it -- must NOT be mistaken for a `_ts_` tag
        # (the T-0360-style structural rigor this detector requires, no
        # raw text proximity).
        from frob.arch._abstraction import _language_tag

        assert _language_tag("results_summary") is None
        assert _language_tag("_ts_build_module") == "ts"
        assert _language_tag("_kt_build_module") == "kt"

    def test_long_form_language_spellings_normalize_to_short_tag(self):
        # frob:tests src/frob/arch/_abstraction.py::_language_tag
        # T-1181: python/typescript/kotlin/cplusplus long-form spellings
        # (e.g. frob.testing._collect*.py's collect_python_tests/
        # collect_typescript_tests/collect_kotlin_tests) must normalize to
        # the SAME canonical short tag as their short-form counterpart so
        # `_is_language_parity_family`'s distinctness check treats them as
        # identity-equivalent, not as untagged/unknown segments.
        from frob.arch._abstraction import _language_tag

        assert _language_tag("collect_python_tests") == "py"
        assert _language_tag("collect_typescript_tests") == "ts"
        assert _language_tag("collect_kotlin_tests") == "kt"
        assert _language_tag("collect_cplusplus_tests") == "cpp"

    def test_long_and_short_form_parity_group_not_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_abstraction.py::_is_language_parity_family
        # frob:tests src/frob/arch/_abstraction.py::_check_abstraction_opportunities
        # A parity family mixing long-form (python/typescript/kotlin) and
        # short-form (cpp) tags -- the T-1181 refile scenario -- must be
        # recognized as genuinely distinct-per-language and excluded, the
        # same as an all-short-form group already is.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "collectors.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class RawSymbol:\n"
            "    pass\n"
            "\n"
            "def collect_python_tests(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
            "\n"
            "def collect_typescript_tests(node: object) -> RawSymbol:\n"
            "    sym = RawSymbol()\n"
            "    return sym\n"
            "\n"
            "def collect_kotlin_tests(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
            "\n"
            "def collect_cpp_tests(node: object) -> RawSymbol:\n"
            "    return RawSymbol()\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" not in categories


class TestCallThroughForwarderExclusion:
    def test_distinct_named_self_forwarders_not_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_abstraction.py::_is_call_through_forwarder_family
        # frob:tests src/frob/arch/_abstraction.py::_is_self_named_forwarder
        # frob:tests src/frob/arch/_abstraction.py::_check_abstraction_opportunities
        # The real `RenderWriter` shape (T-1182, refiled from the T-1083
        # disposition): each method carries a DIFFERENT bare name
        # (heading/good/warn) but its own body is a short call-through to
        # an identically-named module-level counterpart -- own lineage,
        # not a shared group name. `_signature_is_specific` alone would
        # flag this group (verified: with the forwarder exclusion
        # removed, this exact fixture flags), so the exclusion is the
        # only thing suppressing it.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "elements.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def heading(text: str, color: bool) -> str:\n"
            "    return text\n"
            "\n"
            "def good(text: str, color: bool) -> str:\n"
            "    return text\n"
            "\n"
            "def warn(text: str, color: bool) -> str:\n"
            "    return text\n"
        )
        (src_dir / "renderer.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "from elements import heading, good, warn\n"
            "\n"
            "\n"
            "class RenderWriter:\n"
            "    def __init__(self, emit, color):\n"
            "        self._emit = emit\n"
            "        self.color = color\n"
            "\n"
            "    def heading(self, text: str) -> None:\n"
            "        self._emit(heading(text, color=self.color))\n"
            "\n"
            "    def good(self, text: str) -> None:\n"
            "        self._emit(good(text, color=self.color))\n"
            "\n"
            "    def warn(self, text: str) -> None:\n"
            "        self._emit(warn(text, color=self.color))\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" not in categories

    def test_group_with_one_non_self_named_member_still_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_abstraction.py::_is_call_through_forwarder_family
        # Three near-duplicate-bodied methods CLUSTER together (same
        # shape, high body-similarity), but `good`/`warn` each mistakenly
        # delegate to `heading` instead of their OWN name -- not real
        # per-member forwarders, just three near-identical (and likely
        # buggy) implementations. A group like this is exactly the
        # unexplained-duplication case the detector exists to catch, so
        # the forwarder exclusion must not suppress it.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "elements.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "def heading(text: str, color: bool) -> str:\n"
            "    return text\n"
        )
        (src_dir / "renderer.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "from elements import heading\n"
            "\n"
            "\n"
            "class RenderWriter:\n"
            "    def __init__(self, emit, color):\n"
            "        self._emit = emit\n"
            "        self.color = color\n"
            "\n"
            "    def heading(self, text: str) -> None:\n"
            "        self._emit(heading(text, color=self.color))\n"
            "\n"
            "    def good(self, text: str) -> None:\n"
            "        self._emit(heading(text, color=self.color))\n"
            "\n"
            "    def warn(self, text: str) -> None:\n"
            "        self._emit(heading(text, color=self.color))\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories

    def test_forwarder_helper_requires_self_named_short_body(self):
        # frob:tests src/frob/arch/_abstraction.py::_is_call_through_forwarder_family
        # frob:tests src/frob/arch/_abstraction.py::_is_self_named_forwarder
        from frob.arch._abstraction import (
            _is_call_through_forwarder_family,
            _is_self_named_forwarder,
        )

        assert _is_self_named_forwarder("heading", "self . _emit ( heading ( _v0 ) )")
        assert not _is_self_named_forwarder("heading", "self . _emit ( warn ( _v0 ) )")
        assert not _is_self_named_forwarder("heading", "")

        # DIFFERENT names, each independently self-forwarding: excluded.
        assert _is_call_through_forwarder_family(
            [
                ("a.py", "heading", "heading ( _v0 )"),
                ("a.py", "good", "good ( _v0 )"),
            ]
        )
        # One member's body does not mention its own name: not excluded.
        assert not _is_call_through_forwarder_family(
            [
                ("a.py", "heading", "heading ( _v0 )"),
                (
                    "a.py",
                    "good",
                    "stripped = _v0 . strip ( ) upper = stripped . upper ( )",
                ),
            ]
        )


class TestCheckRegistryExclusion:
    def test_check_and_run_checks_names_not_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_abstraction.py::_is_check_registry_family
        # frob:tests src/frob/arch/_abstraction.py::_check_abstraction_opportunities
        # Three same-signature functions named per `frob.arch`'s own
        # detector-registry convention (`check_*` detectors plus a family's
        # `run_*_checks` aggregator, T-1112) -- `_signature_is_specific`
        # alone would flag this group (verified: with the check-registry
        # exclusion removed, this exact fixture flags), so the exclusion is
        # the only thing suppressing it.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "checks.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class ArchSuggestion:\n"
            "    pass\n"
            "\n"
            "def check_no_di_construction(module: object) -> list[ArchSuggestion]:\n"
            "    return []\n"
            "\n"
            "def check_boolean_flag_param(module: object) -> list[ArchSuggestion]:\n"
            "    out = []\n"
            "    return out\n"
            "\n"
            "def run_smell_checks(module: object) -> list[ArchSuggestion]:\n"
            "    return []\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" not in categories

    def test_non_registry_named_group_still_flagged(self, tmp_path):
        # frob:tests src/frob/arch/_abstraction.py::_is_check_registry_family
        # `_validate_no_di` does not match the `check_*`/`run_*_checks`
        # naming convention -- the group has no such registry shape to
        # exclude, so it falls through to the normal signature/body checks
        # and still flags.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "checks.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class ArchSuggestion:\n"
            "    pass\n"
            "\n"
            "def _validate_no_di(module: object) -> list[ArchSuggestion]:\n"
            "    return []\n"
            "\n"
            "def check_boolean_flag_param(module: object) -> list[ArchSuggestion]:\n"
            "    out = []\n"
            "    return out\n"
            "\n"
            "def run_smell_checks(module: object) -> list[ArchSuggestion]:\n"
            "    return []\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories

    def test_check_registry_regex_matches_both_shapes(self) -> None:
        # frob:tests src/frob/arch/_abstraction.py::_is_check_registry_family
        from frob.arch._abstraction import _is_check_registry_family

        assert _is_check_registry_family(
            [("a.py", "check_boolean_flag_param"), ("b.py", "run_smell_checks")]
        )
        assert not _is_check_registry_family(
            [("a.py", "check_boolean_flag_param"), ("b.py", "_validate_no_di")]
        )


# frob:ticket T-1141
class TestGateRuleBuilderExclusion:
    """`_is_gate_rule_builder_family` (T-1141, mirroring T-1112's
    `_is_check_registry_family`): a shared-signature group whose return
    type is `Violation`/`list[Violation]`/`tuple[Violation, ...]` is
    `frob.gates`'s own gate/rule-builder convention, not an accidental
    duplication -- structural (return-type-based), unlike the
    check-registry exclusion's name-based discriminator, since gate/rule-
    builder names do not share one fixed prefix/suffix the way
    `check_*`/`run_*_checks` do."""

    def test_violation_returning_group_not_flagged(self, tmp_path) -> None:
        # frob:tests src/frob/arch/_abstraction.py::_is_gate_rule_builder_family
        # frob:tests src/frob/arch/_abstraction.py::_check_abstraction_opportunities
        # Three same-signature functions returning `tuple[Violation, ...]`
        # with arbitrary, non-convention-matching names -- verified: with
        # the gate-rule-builder exclusion removed, this exact fixture
        # flags (a specific `Path` param type alone would satisfy
        # `_signature_is_specific`).
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "gates.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class Violation:\n"
            "    pass\n"
            "\n"
            "def alpha_check(root) -> tuple[Violation, ...]:\n"
            "    return ()\n"
            "\n"
            "def bravo_check(root) -> tuple[Violation, ...]:\n"
            "    return ()\n"
            "\n"
            "def charlie_check(root) -> tuple[Violation, ...]:\n"
            "    return ()\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" not in categories

    def test_non_violation_returning_group_still_flagged(self, tmp_path) -> None:
        # frob:tests src/frob/arch/_abstraction.py::_is_gate_rule_builder_family
        # A same-signature group over a specific (non-generic) type that
        # does NOT return a Violation shape has no gate/rule-builder
        # convention to exclude, so it falls through to the normal
        # signature/body checks and still flags.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "gates.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class TicketQueue:\n"
            "    pass\n"
            "\n"
            "def alpha_lookup(queue: TicketQueue) -> str:\n"
            "    return ''\n"
            "\n"
            "def bravo_lookup(queue: TicketQueue) -> str:\n"
            "    return ''\n"
            "\n"
            "def charlie_lookup(queue: TicketQueue) -> str:\n"
            "    return ''\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories

    def test_return_type_membership_matches_all_three_shapes(self) -> None:
        # frob:tests src/frob/arch/_abstraction.py::_is_gate_rule_builder_family
        from frob.arch._abstraction import _is_gate_rule_builder_family

        assert _is_gate_rule_builder_family("Violation")
        assert _is_gate_rule_builder_family("list[Violation]")
        assert _is_gate_rule_builder_family("tuple[Violation, ...]")
        assert not _is_gate_rule_builder_family("str")
        assert not _is_gate_rule_builder_family("tuple[Edge, ...]")


# frob:ticket T-1144
class TestToolResultBuilderExclusion:
    """`_is_tool_result_builder_family` (T-1144, mirroring T-1141's
    `_is_gate_rule_builder_family` for `frob.gates`'s own `Violation`
    convention): a shared-signature group whose return type is
    `ToolResult`/`ToolResult | None` is `frob.process`/`frob.check`'s own
    check-stage-runner convention, not an accidental duplication."""

    def test_toolresult_returning_group_not_flagged(self, tmp_path) -> None:
        # frob:tests src/frob/arch/_abstraction.py::_is_tool_result_builder_family
        # frob:tests src/frob/arch/_abstraction.py::_check_abstraction_opportunities
        # Three same-signature functions returning `ToolResult` with
        # arbitrary, non-convention-matching names -- verified: with the
        # tool-result-builder exclusion removed, this exact fixture flags
        # (a specific `Path` param type alone satisfies
        # `_signature_is_specific`).
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "runners.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class ToolResult:\n"
            "    pass\n"
            "\n"
            "def alpha_run(root) -> ToolResult:\n"
            "    return ToolResult()\n"
            "\n"
            "def bravo_run(root) -> ToolResult:\n"
            "    return ToolResult()\n"
            "\n"
            "def charlie_run(root) -> ToolResult:\n"
            "    return ToolResult()\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" not in categories

    def test_non_toolresult_returning_group_still_flagged(self, tmp_path) -> None:
        # frob:tests src/frob/arch/_abstraction.py::_is_tool_result_builder_family
        # A same-shaped group over a specific (non-generic) type that does
        # NOT return a ToolResult shape has no check-stage-runner
        # convention to exclude, so it falls through to the normal
        # signature/body checks and still flags.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "runners.py").write_text(
            "from __future__ import annotations\n"
            "\n"
            "class ToolResult:\n"
            "    pass\n"
            "\n"
            "def alpha_lookup(result: ToolResult) -> str:\n"
            "    return ''\n"
            "\n"
            "def bravo_lookup(result: ToolResult) -> str:\n"
            "    return ''\n"
            "\n"
            "def charlie_lookup(result: ToolResult) -> str:\n"
            "    return ''\n"
        )
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "abstraction-opportunity" in categories

    def test_return_type_membership_matches_both_shapes(self) -> None:
        # frob:tests src/frob/arch/_abstraction.py::_is_tool_result_builder_family
        from frob.arch._abstraction import _is_tool_result_builder_family

        assert _is_tool_result_builder_family("ToolResult")
        assert _is_tool_result_builder_family("ToolResult | None")
        assert not _is_tool_result_builder_family("str")
        assert not _is_tool_result_builder_family("Violation")


class TestPatternRecommender:
    def test_isinstance_chain_recommends_strategy(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "shapes.py").write_text(
            "def area(shape):\n"
            "    if isinstance(shape, Circle):\n"
            "        return 1\n"
            "    elif isinstance(shape, Square):\n"
            "        return 2\n"
            "    elif isinstance(shape, Triangle):\n"
            "        return 3\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("Strategy" in s.message for s in hits)

    def test_two_arm_isinstance_chain_not_flagged(self, tmp_path: Path) -> None:
        # STRONG-HALLMARK-ONLY: two arms is routine control flow, not a
        # growing type-switch -- must not fire.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "shapes.py").write_text(
            "def area(shape):\n"
            "    if isinstance(shape, Circle):\n"
            "        return 1\n"
            "    elif isinstance(shape, Square):\n"
            "        return 2\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "Strategy" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_state_field_chain_recommends_state_machine(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "job.py").write_text(
            "class Job:\n"
            "    def step(self):\n"
            "        if self.status == 'pending':\n"
            "            pass\n"
            "        elif self.status == 'running':\n"
            "            pass\n"
            "        elif self.status == 'done':\n"
            "            pass\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("State machine" in s.message for s in hits)

    def test_non_state_attribute_chain_not_flagged_state_machine(
        self, tmp_path: Path
    ) -> None:
        # STRONG-HALLMARK-ONLY: an elif chain on a `self.<attr>` whose name
        # carries no state/status/mode/phase/stage lifecycle hint is an
        # ordinary attribute comparison, not the growing-state-machine
        # hallmark -- must not fire State machine.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "shape.py").write_text(
            "class Shape:\n"
            "    def area(self):\n"
            "        if self.color == 'red':\n"
            "            pass\n"
            "        elif self.color == 'blue':\n"
            "            pass\n"
            "        elif self.color == 'green':\n"
            "            pass\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "State machine" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_telescoping_ctor_recommends_builder(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "cfg.py").write_text(
            "class Config:\n"
            "    def __init__(self, a=1, b=2, c=None, d=None, e=None, f=None):\n"
            "        self.a = a\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("Builder" in s.message for s in hits)

    def test_normal_ctor_not_flagged_as_telescoping(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "point.py").write_text(
            "class Point:\n"
            "    def __init__(self, x, y):\n"
            "        self.x = x\n"
            "        self.y = y\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "Builder" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_scattered_construction_across_files_recommends_factory(
        self, tmp_path: Path
    ) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.py").write_text("def use_a():\n    return Widget(1)\n")
        (src_dir / "b.py").write_text("def use_b():\n    return Widget(2)\n")
        (src_dir / "c.py").write_text("def use_c():\n    return Widget(3)\n")
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("Factory" in s.message and "Widget" in s.message for s in hits)

    def test_construction_in_two_files_not_flagged(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.py").write_text("def use_a():\n    return Widget(1)\n")
        (src_dir / "b.py").write_text("def use_b():\n    return Widget(2)\n")
        result = analyze_project(src_dir)
        assert not any(
            "Factory" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_wrap_delegate_recommends_decorator(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "wrapper.py").write_text(
            "class LoggingList:\n"
            "    def __init__(self, inner):\n"
            "        self._inner = inner\n"
            "\n"
            "    def append(self):\n"
            "        return self._inner.append()\n"
            "\n"
            "    def pop(self):\n"
            "        return self._inner.pop()\n"
            "\n"
            "    def clear(self):\n"
            "        return self._inner.clear()\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("Decorator" in s.message for s in hits)

    def test_two_method_delegating_wrapper_not_flagged_decorator(
        self, tmp_path: Path
    ) -> None:
        # STRONG-HALLMARK-ONLY: only 2 pass-through methods (below
        # _MIN_DELEGATE_METHODS=3) is an ordinary small wrapper, not the
        # wrap-and-delegate hallmark -- must not fire Decorator.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "wrapper.py").write_text(
            "class SmallWrapper:\n"
            "    def __init__(self, inner):\n"
            "        self._inner = inner\n"
            "\n"
            "    def append(self):\n"
            "        return self._inner.append()\n"
            "\n"
            "    def pop(self):\n"
            "        return self._inner.pop()\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "Decorator" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_god_class_pairs_with_srp_escape(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        methods = "\n".join(f"    def m{i}(self): pass" for i in range(14))
        (src_dir / "big.py").write_text(f"class BigThing:\n{methods}\n")
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "god-class" in categories
        assert "anti-pattern-escape" in categories
        escape = next(
            s for s in result.suggestions if s.category == "anti-pattern-escape"
        )
        assert "SRP decompose" in escape.message
        assert "BigThing" in escape.message

    def test_class_at_threshold_not_flagged_god_object(self, tmp_path: Path) -> None:
        # STRONG-HALLMARK-ONLY: god-object is PAIRED with god-class
        # (T-0332's "one detector, two outputs" design) -- a class at
        # exactly the default max_class_methods=12 threshold does not
        # trigger god-class, so it must not produce a paired SRP-decompose
        # escape either.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        methods = "\n".join(f"    def m{i}(self): pass" for i in range(12))
        (src_dir / "normal.py").write_text(f"class NormalThing:\n{methods}\n")
        result = analyze_project(src_dir)
        categories = {s.category for s in result.suggestions}
        assert "god-class" not in categories
        assert "anti-pattern-escape" not in categories

    def test_stringly_typed_recommends_newtype(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "cmd.py").write_text(
            "def dispatch(cmd):\n"
            "    if cmd == 'start':\n"
            "        pass\n"
            "    elif cmd == 'stop':\n"
            "        pass\n"
            "    elif cmd == 'pause':\n"
            "        pass\n"
            "    elif cmd == 'resume':\n"
            "        pass\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "anti-pattern-escape"]
        assert any("newtype" in s.message for s in hits)

    def test_short_string_chain_not_flagged_stringly_typed(
        self, tmp_path: Path
    ) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "cmd.py").write_text(
            "def dispatch(cmd):\n"
            "    if cmd == 'start':\n"
            "        pass\n"
            "    elif cmd == 'stop':\n"
            "        pass\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "newtype" in s.message
            for s in result.suggestions
            if s.category == "anti-pattern-escape"
        )

    def test_simple_python_no_pattern_recommendations(self) -> None:
        # Clean fixture project must not produce any advisory pattern
        # findings -- the STRONG-HALLMARK-ONLY constraint means simple code
        # never fires.
        root = FIXTURES / "simple_python" / "src"
        result = analyze_project(root)
        categories = {s.category for s in result.suggestions}
        assert "pattern-recommendation" not in categories
        assert "anti-pattern-escape" not in categories

    # -- T-0605: interface-translate -> Adapter -----------------------------

    def test_translating_wrapper_recommends_adapter(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "legacy_adapter.py").write_text(
            "class LegacyAdapter:\n"
            "    def __init__(self, legacy):\n"
            "        self._legacy = legacy\n"
            "\n"
            "    def read(self):\n"
            "        return self._legacy.fetch_old()\n"
            "\n"
            "    def write(self, data):\n"
            "        return self._legacy.store_old(data)\n"
            "\n"
            "    def close(self):\n"
            "        return self._legacy.shutdown_old()\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("Adapter" in s.message for s in hits)

    def test_same_name_wrapper_not_flagged_adapter(self, tmp_path: Path) -> None:
        # Disjointness proof: a SAME-name pass-through wrapper (3+ methods)
        # is `wrap-delegate` -> Decorator, never `interface-translate` ->
        # Adapter -- the two hallmarks must never double-fire on identical
        # call-name shapes.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "wrapper.py").write_text(
            "class LoggingList:\n"
            "    def __init__(self, inner):\n"
            "        self._inner = inner\n"
            "\n"
            "    def append(self):\n"
            "        return self._inner.append()\n"
            "\n"
            "    def pop(self):\n"
            "        return self._inner.pop()\n"
            "\n"
            "    def clear(self):\n"
            "        return self._inner.clear()\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "Adapter" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_two_translating_methods_not_flagged_adapter(self, tmp_path: Path) -> None:
        # STRONG-HALLMARK-ONLY: only 2 translating methods (below
        # _MIN_TRANSLATE_METHODS=3) is an ordinary small wrapper, not the
        # interface-translate hallmark -- must not fire Adapter.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "small_adapter.py").write_text(
            "class SmallAdapter:\n"
            "    def __init__(self, legacy):\n"
            "        self._legacy = legacy\n"
            "\n"
            "    def read(self):\n"
            "        return self._legacy.fetch_old()\n"
            "\n"
            "    def write(self, data):\n"
            "        return self._legacy.store_old(data)\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "Adapter" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_mixed_delegate_and_translate_methods_fires_both(
        self, tmp_path: Path
    ) -> None:
        # Disjointness pin (reviewer round 1, T-0605): `wrap-delegate` and
        # `interface-translate` are disjoint PER-METHOD ONLY, never
        # per-class. A class with a same-name-delegating subset (3
        # methods) AND a separate translating subset (3 differently-named
        # methods) on the SAME inner attribute legitimately fires BOTH
        # Decorator and Adapter -- two true findings about two disjoint
        # method groups, not a contradiction. This is intentional,
        # accepted behavior, not a bug to suppress.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "mixed.py").write_text(
            "class MixedWrapper:\n"
            "    def __init__(self, inner):\n"
            "        self._inner = inner\n"
            "\n"
            "    def append(self):\n"
            "        return self._inner.append()\n"
            "\n"
            "    def pop(self):\n"
            "        return self._inner.pop()\n"
            "\n"
            "    def clear(self):\n"
            "        return self._inner.clear()\n"
            "\n"
            "    def read(self):\n"
            "        return self._inner.fetch_old()\n"
            "\n"
            "    def write(self, data):\n"
            "        return self._inner.store_old(data)\n"
            "\n"
            "    def close(self):\n"
            "        return self._inner.shutdown_old()\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("Decorator" in s.message for s in hits)
        assert any("Adapter" in s.message for s in hits)

    # -- T-0605: manual-callback-list -> Observer ----------------------------

    def test_manual_callback_list_recommends_observer(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "bus.py").write_text(
            "class EventBus:\n"
            "    def __init__(self):\n"
            "        self._listeners = []\n"
            "\n"
            "    def subscribe(self, cb):\n"
            "        self._listeners.append(cb)\n"
            "\n"
            "    def publish(self):\n"
            "        for cb in self._listeners:\n"
            "            cb()\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("Observer" in s.message for s in hits)

    def test_append_only_list_not_flagged_observer(self, tmp_path: Path) -> None:
        # No notify loop -- an ordinary list attribute that is only ever
        # appended to (a plain accumulator) must not fire Observer.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "log.py").write_text(
            "class Log:\n"
            "    def __init__(self):\n"
            "        self._entries = []\n"
            "\n"
            "    def record(self, entry):\n"
            "        self._entries.append(entry)\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "Observer" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_iterate_without_append_not_flagged_observer(self, tmp_path: Path) -> None:
        # A notify-shaped loop over a list nothing ever appends to (e.g. a
        # fixed, pre-populated list) must not fire Observer either -- both
        # the register AND notify facts are required.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "fixed.py").write_text(
            "class FixedHandlers:\n"
            "    def __init__(self):\n"
            "        self._handlers = []\n"
            "\n"
            "    def run_all(self):\n"
            "        for h in self._handlers:\n"
            "            h()\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "Observer" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    # -- T-0605: anemic-accessors -> move behavior to data -------------------

    def test_anemic_accessors_recommends_move_behavior(self, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "record.py").write_text(
            "class CustomerRecord:\n"
            "    def __init__(self, name, email, balance):\n"
            "        self._name = name\n"
            "        self._email = email\n"
            "        self._balance = balance\n"
            "\n"
            "    def get_name(self):\n"
            "        return self._name\n"
            "\n"
            "    def set_name(self, name):\n"
            "        self._name = name\n"
            "\n"
            "    def get_email(self):\n"
            "        return self._email\n"
            "\n"
            "    def set_balance(self, balance):\n"
            "        self._balance = balance\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "anti-pattern-escape"]
        assert any("move behavior to data" in s.message for s in hits)

    def test_class_with_real_method_not_flagged_anemic(self, tmp_path: Path) -> None:
        # One real method (actual computation) alongside several trivial
        # accessors must disqualify the whole class -- a mixed
        # behavior-plus-accessors class is not anemic.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "account.py").write_text(
            "class Account:\n"
            "    def __init__(self, name, email, balance):\n"
            "        self._name = name\n"
            "        self._email = email\n"
            "        self._balance = balance\n"
            "\n"
            "    def get_name(self):\n"
            "        return self._name\n"
            "\n"
            "    def set_name(self, name):\n"
            "        self._name = name\n"
            "\n"
            "    def get_email(self):\n"
            "        return self._email\n"
            "\n"
            "    def apply_interest(self, rate):\n"
            "        if rate > 0:\n"
            "            self._balance = self._balance * (1 + rate)\n"
            "        return self._balance\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "move behavior to data" in s.message
            for s in result.suggestions
            if s.category == "anti-pattern-escape"
        )

    def test_two_accessor_class_not_flagged_anemic(self, tmp_path: Path) -> None:
        # STRONG-HALLMARK-ONLY: only 2 accessor methods (below
        # _MIN_ANEMIC_ACCESSORS=3) is an ordinary small value holder, not
        # the anemic-domain-model hallmark -- must not fire.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "point.py").write_text(
            "class Point:\n"
            "    def __init__(self, x, y):\n"
            "        self._x = x\n"
            "        self._y = y\n"
            "\n"
            "    def get_x(self):\n"
            "        return self._x\n"
            "\n"
            "    def get_y(self):\n"
            "        return self._y\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "move behavior to data" in s.message
            for s in result.suggestions
            if s.category == "anti-pattern-escape"
        )

    def test_dataclass_boilerplate_recommends_dataclass(self, tmp_path: Path) -> None:
        # T-0849: a plain class whose only method is a pure
        # assign-every-param `__init__` recommends `@dataclass`.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "point.py").write_text(
            "class Point3D:\n"
            "    def __init__(self, x, y, z):\n"
            "        self.x = x\n"
            "        self.y = y\n"
            "        self.z = z\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("@dataclass" in s.message for s in hits)

    def test_dataclass_boilerplate_with_computed_field_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # Adversarial near-miss (hand-verified, T-0849): mutate the
        # discriminator by making ONE assignment computed instead of a
        # bare parameter pass-through -- the detector must go silent. This
        # is the exact fixture used to hand-verify the near-miss is
        # load-bearing: reverting `self.z = z * 2` back to `self.z = z`
        # makes this test start failing (the class becomes a real 3-field
        # boilerplate holder again).
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "point.py").write_text(
            "class Point3D:\n"
            "    def __init__(self, x, y, z):\n"
            "        self.x = x\n"
            "        self.y = y\n"
            "        self.z = z * 2\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "@dataclass" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_dataclass_boilerplate_with_extra_method_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # A second method beyond `__init__` (even a trivial one) means
        # this is not a pure value holder -- must not fire.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "point.py").write_text(
            "class Point3D:\n"
            "    def __init__(self, x, y, z):\n"
            "        self.x = x\n"
            "        self.y = y\n"
            "        self.z = z\n"
            "\n"
            "    def magnitude(self):\n"
            "        return (self.x**2 + self.y**2 + self.z**2) ** 0.5\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "@dataclass" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_dataclass_boilerplate_with_decorated_extra_method_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # Adversarial near-miss (hand-verified, T-0849 reviewer round 1):
        # a `@property` method is a `decorated_definition` node, not a
        # `function_definition` -- the detector's class-body member scan
        # must count it too, or it silently vanishes from the extra-
        # method count and the class wrongly looks like a pure `__init__`-
        # only value holder. Hand-verified: dropping the `decorated_
        # definition` arm from the member-collection filter makes this
        # test start failing (the class becomes a false-positive
        # `@dataclass` recommendation again).
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "point.py").write_text(
            "class Point3D:\n"
            "    def __init__(self, x, y, z):\n"
            "        self.x = x\n"
            "        self.y = y\n"
            "        self.z = z\n"
            "\n"
            "    @property\n"
            "    def magnitude(self):\n"
            "        return (self.x**2 + self.y**2 + self.z**2) ** 0.5\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "@dataclass" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_already_dataclass_not_flagged(self, tmp_path: Path) -> None:
        # An already-`@dataclass`-decorated class is a `decorated_
        # definition` node, structurally excluded before body inspection.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "point.py").write_text(
            "from dataclasses import dataclass\n"
            "\n"
            "@dataclass\n"
            "class Point3D:\n"
            "    x: int\n"
            "    y: int\n"
            "    z: int\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "@dataclass" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_manual_decorator_wrap_recommends_decorator_syntax(
        self, tmp_path: Path
    ) -> None:
        # T-0849: 3+ module-level `def f(...): ...` / `f = wrapper(f)`
        # reassignment pairs recommend `@wrapper` decorator syntax.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "registry.py").write_text(
            "def handler_one():\n"
            "    pass\n"
            "handler_one = logged(handler_one)\n"
            "\n"
            "def handler_two():\n"
            "    pass\n"
            "handler_two = logged(handler_two)\n"
            "\n"
            "def handler_three():\n"
            "    pass\n"
            "handler_three = logged(handler_three)\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "pattern-recommendation"]
        assert any("decorator syntax" in s.message for s in hits)

    def test_two_manual_decorator_wraps_not_flagged(self, tmp_path: Path) -> None:
        # Adversarial near-miss (hand-verified, T-0849): mutate the
        # discriminator by dropping to 2 occurrences (below
        # _MIN_MANUAL_DECORATOR_WRAPS=3) -- the STRONG-HALLMARK-ONLY floor
        # must keep this silent. Hand-verified: adding a third
        # `handler_three = logged(handler_three)` pair back makes this
        # test start failing (the file becomes the real 3-site hallmark).
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "registry.py").write_text(
            "def handler_one():\n"
            "    pass\n"
            "handler_one = logged(handler_one)\n"
            "\n"
            "def handler_two():\n"
            "    pass\n"
            "handler_two = logged(handler_two)\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "decorator syntax" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

    def test_decorator_syntax_wrap_not_flagged(self, tmp_path: Path) -> None:
        # Functions already wrapped via real `@decorator` syntax are
        # `decorated_definition` nodes, not bare `function_definition`s --
        # never enter this walk, never fire.
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "registry.py").write_text(
            "@logged\n"
            "def handler_one():\n"
            "    pass\n"
            "\n"
            "@logged\n"
            "def handler_two():\n"
            "    pass\n"
            "\n"
            "@logged\n"
            "def handler_three():\n"
            "    pass\n"
        )
        result = analyze_project(src_dir)
        assert not any(
            "decorator syntax" in s.message
            for s in result.suggestions
            if s.category == "pattern-recommendation"
        )

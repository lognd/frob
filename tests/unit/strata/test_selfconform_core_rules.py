"""Unit tests for T-4110/H3-10: SYS113, a `code=`/`via` declaration glob
matching zero real files as its own finding, distinct from SYS101
(declared but never OBSERVED, which requires the glob to match at least
one real file). `frob.strata._selfconform_core_rules` holds the
violation-construction code this file exercises via the public
`check_self_conformance` entry point (`_selfconform.py`), the same way
every other SYS10x sibling suite in `test_selfconform.py` does.
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import (
    SYS_STALE_DESIGN,
    KernelModel,
    MayGrant,
    Node,
    check_self_conformance,
)
from frob.strata._selfconform import SYS_ZERO_MATCH_DECLARATION


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestZeroMatchCodeGlob:
    """A node's whole `code=` glob set matching zero real files (H3-10's
    "the code is not here at all" case) fires SYS113, never SYS101."""

    # frob:tests \
    # src/frob/strata/_selfconform_core_rules.py::_zero_match_declaration_violations \
    # kind="unit"
    def test_must_fire_when_code_glob_matches_nothing(self, tmp_path: Path) -> None:
        """A node whose `code=` glob names a directory that does not exist
        anywhere in the tree at all (a renamed module, a stale glob) is
        SYS113, not silently folded into a SYS101 "declared but never
        observed" finding on every one of its `may` atoms."""
        # Deliberately no file under src/frob/widget/** at all.
        _write(tmp_path, "src/frob/other/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok, result.err
        zero_match = [
            v
            for v in result.danger_ok.violations
            if v.rule == SYS_ZERO_MATCH_DECLARATION
        ]
        assert any(v.node == "widget" for v in zero_match)

    # frob:tests \
    # src/frob/strata/_selfconform_core_rules.py::_zero_match_declaration_violations \
    # kind="unit"
    def test_must_not_fire_when_glob_matches_real_files_with_zero_observed_capability(
        self, tmp_path: Path
    ) -> None:
        """A node whose glob matches >=1 REAL file, none of which exercises
        the declared capability, is the already-covered case: SYS101
        fires, SYS113 must stay quiet -- these two facts are exactly what
        H3-10 says must never collapse into one signal."""
        _write(tmp_path, "src/frob/widget/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok, result.err
        rules = {v.rule for v in result.danger_ok.violations if v.node == "widget"}
        assert SYS_STALE_DESIGN in rules
        assert SYS_ZERO_MATCH_DECLARATION not in rules

    # frob:tests \
    # src/frob/strata/_selfconform_core_rules.py::_zero_match_declaration_violations \
    # kind="unit"
    def test_must_not_fire_when_glob_matches_real_files_that_exercise_capability(
        self, tmp_path: Path
    ) -> None:
        """The clean case: a glob matches >=1 real file that DOES exercise
        the declared capability -- neither SYS101 nor SYS113 fires."""
        _write(
            tmp_path,
            "src/frob/widget/_io.py",
            "import requests\nrequests.get('x')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok, result.err
        rules = {v.rule for v in result.danger_ok.violations if v.node == "widget"}
        assert SYS_STALE_DESIGN not in rules
        assert SYS_ZERO_MATCH_DECLARATION not in rules

    # frob:tests \
    # src/frob/strata/_selfconform_core_rules.py::_zero_match_declaration_violations \
    # kind="unit"
    def test_must_not_fire_for_fully_graph_excluded_node(self, tmp_path: Path) -> None:
        """A node whose entire `code=` glob resolves ONLY to
        `[graph].exclude`'d paths (>=1 real match, all excluded) is the
        `_fully_excluded_node_ids` carve-out (T-0310) -- a real,
        pre-existing zero-match-after-exclusion case, structurally
        distinct from SYS113's "matches nothing at all". Neither SYS101
        nor SYS113 may fire for it."""
        _write(tmp_path, "src/frob/widget/excluded/_io.py", "x = 1\n")
        (tmp_path / "frob.toml").write_text(
            '[graph]\nexclude = ["src/frob/widget/excluded/**"]\n', encoding="utf-8"
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/excluded/**",),
                    may=("net",),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok, result.err
        rules = {v.rule for v in result.danger_ok.violations if v.node == "widget"}
        assert SYS_STALE_DESIGN not in rules
        assert SYS_ZERO_MATCH_DECLARATION not in rules


class TestZeroMatchViaEntry:
    """A glob-form (non-symbol) `may` grant `via` entry matching zero of
    its own node's bound files fires SYS113 -- the per-declaration
    sibling of `TestZeroMatchCodeGlob`, narrowed to one grant's own `via`
    surface rather than the whole node's `code=` set."""

    # frob:tests \
    # src/frob/strata/_selfconform_core_rules.py::_zero_match_declaration_violations \
    # kind="unit"
    def test_must_fire_when_via_glob_matches_no_owned_file(
        self, tmp_path: Path
    ) -> None:
        """T-4110/H3-10's own example: a `may "net" via "path/glob"` entry
        whose glob names a file that is not among the node's own bound
        files (a typo, a rename, a deleted file) is SYS113."""
        _write(tmp_path, "src/frob/widget/_net_a.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net",),
                    may_grants=(
                        MayGrant(
                            atom="net",
                            via=("src/frob/widget/_net_typo.py",),
                        ),
                    ),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok, result.err
        zero_match = [
            v
            for v in result.danger_ok.violations
            if v.rule == SYS_ZERO_MATCH_DECLARATION
        ]
        assert any(
            v.node == "widget" and "_net_typo.py" in v.detail for v in zero_match
        )

    # frob:tests \
    # src/frob/strata/_selfconform_core_rules.py::_zero_match_declaration_violations \
    # kind="unit"
    def test_must_not_fire_for_symbol_form_via_matching_zero_files(
        self, tmp_path: Path
    ) -> None:
        """A SYMBOL-form `via` entry (`glob::symbol`) resolving against
        zero candidate files is SYS109's territory
        (`check_stale_via_symbols`), not SYS113's -- covering it again
        here would double-report the identical fact under two rule ids."""
        _write(tmp_path, "src/frob/widget/_net_a.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net",),
                    may_grants=(
                        MayGrant(
                            atom="net",
                            via=("src/frob/widget/_net_typo.py::send",),
                        ),
                    ),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok, result.err
        zero_match = [
            v
            for v in result.danger_ok.violations
            if v.rule == SYS_ZERO_MATCH_DECLARATION
        ]
        assert zero_match == []

    # frob:tests \
    # src/frob/strata/_selfconform_core_rules.py::_zero_match_declaration_violations \
    # kind="unit"
    def test_must_not_fire_when_via_glob_matches_owned_file(
        self, tmp_path: Path
    ) -> None:
        """A `via` entry that DOES match one of the node's own bound files
        is a real, well-formed declaration -- neither SYS113 nor (once
        exercised) SYS101 fires for it."""
        _write(
            tmp_path,
            "src/frob/widget/_net_a.py",
            "import requests\nrequests.get('x')\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                    may=("net",),
                    may_grants=(
                        MayGrant(atom="net", via=("src/frob/widget/_net_a.py",)),
                    ),
                ),
            )
        )
        result = check_self_conformance(model, tmp_path)
        assert result.is_ok, result.err
        rules = {v.rule for v in result.danger_ok.violations if v.node == "widget"}
        assert SYS_ZERO_MATCH_DECLARATION not in rules
        assert SYS_STALE_DESIGN not in rules

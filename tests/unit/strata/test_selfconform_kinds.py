"""Unit tests for the T-4110/H3-10 shared kinds-layer joins:
`_selfconform_kinds.py::_matched_real_files`/`_zero_match_node_code_ids`/
`_zero_match_via_entries` -- the "does this glob resolve to any real file
at all" computation `_selfconform_core_rules.py`'s SYS113 violation
builders consume. These exercise the joins directly (no `KernelModel`
round-trip through `check_self_conformance`), the same layer-1-only style
`_fully_excluded_node_ids` itself would be unit-tested at.
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, MayGrant, Node
from frob.strata._code_binding import CodeBinding, bind_code
from frob.strata._selfconform_kinds import (
    _fully_excluded_node_ids,
    _matched_real_files,
    _zero_match_node_code_ids,
    _zero_match_via_entries,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestMatchedRealFiles:
    # frob:tests src/frob/strata/_selfconform_kinds.py::_matched_real_files kind="unit"
    def test_returns_only_matching_files(self) -> None:
        all_files = ["a/x.py", "a/y.py", "b/z.py"]
        assert _matched_real_files(["a/*.py"], all_files) == ["a/x.py", "a/y.py"]

    # frob:tests src/frob/strata/_selfconform_kinds.py::_matched_real_files kind="unit"
    def test_empty_when_no_glob_matches(self) -> None:
        all_files = ["a/x.py"]
        assert _matched_real_files(["nope/**"], all_files) == []


class TestZeroMatchNodeCodeIds:
    # frob:tests src/frob/strata/_selfconform_kinds.py::_zero_match_node_code_ids \
    # kind="unit"
    def test_node_with_zero_matching_files_is_flagged(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/frob/other/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                ),
            )
        )
        assert _zero_match_node_code_ids(model, tmp_path) == frozenset({"widget"})

    # frob:tests src/frob/strata/_selfconform_kinds.py::_zero_match_node_code_ids \
    # kind="unit"
    def test_node_with_at_least_one_matching_file_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        _write(tmp_path, "src/frob/widget/_io.py", "x = 1\n")
        model = KernelModel(
            nodes=(
                Node(
                    id="widget",
                    trust="trusted",
                    attrs=("code=src/frob/widget/**",),
                ),
            )
        )
        assert _zero_match_node_code_ids(model, tmp_path) == frozenset()

    # frob:tests src/frob/strata/_selfconform_kinds.py::_zero_match_node_code_ids \
    # kind="unit"
    def test_node_with_no_code_glob_at_all_is_skipped(self, tmp_path: Path) -> None:
        model = KernelModel(
            nodes=(Node(id="widget", trust="trusted", attrs=()),)
        )
        assert _zero_match_node_code_ids(model, tmp_path) == frozenset()

    # frob:tests src/frob/strata/_selfconform_kinds.py::_zero_match_node_code_ids \
    # kind="unit"
    def test_disjoint_from_fully_excluded_node_ids(self, tmp_path: Path) -> None:
        """A node whose glob matches >=1 real file, all graph-excluded, is
        `_fully_excluded_node_ids`'s own carve-out (>=1 match) -- it must
        NEVER also appear in `_zero_match_node_code_ids` (zero matches),
        the exact disjointness H3-10 depends on to keep the two rules from
        double-firing on the same node."""
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
                ),
            )
        )
        excluded = _fully_excluded_node_ids(model, tmp_path)
        zero_match = _zero_match_node_code_ids(model, tmp_path)
        assert excluded == frozenset({"widget"})
        assert zero_match == frozenset()
        assert excluded.isdisjoint(zero_match)


class TestZeroMatchViaEntries:
    # frob:tests src/frob/strata/_selfconform_kinds.py::_zero_match_via_entries \
    # kind="unit"
    def test_glob_form_via_matching_no_owned_file_is_flagged(
        self, tmp_path: Path
    ) -> None:
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
                            atom="net", via=("src/frob/widget/_net_typo.py",)
                        ),
                    ),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        found = _zero_match_via_entries(model, binding, tmp_path)
        assert found == [
            ("widget", "net", "src/frob/widget/_net_typo.py"),
        ]

    # frob:tests src/frob/strata/_selfconform_kinds.py::_zero_match_via_entries \
    # kind="unit"
    def test_glob_form_via_matching_owned_file_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        _write(tmp_path, "src/frob/widget/_net_a.py", "x = 1\n")
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
        binding = bind_code(model, tmp_path).danger_ok
        assert _zero_match_via_entries(model, binding, tmp_path) == []

    # frob:tests src/frob/strata/_selfconform_kinds.py::_zero_match_via_entries \
    # kind="unit"
    def test_symbol_form_via_is_never_flagged_even_when_matching_nothing(
        self, tmp_path: Path
    ) -> None:
        """Symbol-form entries are SYS109's territory -- this function must
        never report them, regardless of match count."""
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
        binding = bind_code(model, tmp_path).danger_ok
        assert _zero_match_via_entries(model, binding, tmp_path) == []

    # frob:tests src/frob/strata/_selfconform_kinds.py::_zero_match_via_entries \
    # kind="unit"
    def test_via_naming_a_graph_excluded_real_file_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """A `via` entry naming a file that genuinely exists but is
        `[graph].exclude`'d is the SAME legitimate carve-out
        `_fully_excluded_node_ids` grants at node granularity -- it must
        NOT fire SYS113, since capability observation could never have
        seen that file either way regardless of the `via` declaration."""
        _write(tmp_path, "src/frob/widget/excluded/_net.py", "x = 1\n")
        (tmp_path / "frob.toml").write_text(
            '[graph]\nexclude = ["src/frob/widget/excluded/**"]\n', encoding="utf-8"
        )
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
                            via=("src/frob/widget/excluded/_net.py",),
                        ),
                    ),
                ),
            )
        )
        binding = bind_code(model, tmp_path).danger_ok
        assert _zero_match_via_entries(model, binding, tmp_path) == []

    # frob:tests src/frob/strata/_selfconform_kinds.py::_zero_match_via_entries \
    # kind="unit"
    def test_node_with_no_may_grants_yields_nothing(self, tmp_path: Path) -> None:
        model = KernelModel(
            nodes=(Node(id="widget", trust="trusted", attrs=()),)
        )
        binding = CodeBinding(owner={})
        assert _zero_match_via_entries(model, binding, tmp_path) == []

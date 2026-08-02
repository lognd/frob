"""Unit tests for frob.strata._design_load (T-0080, T-0084)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from frob.graph import Edge, EdgeKind, GraphSnapshot
from frob.strata import DesignIds, StrataError, load_design_ids
from frob.strata._design_load import DesignLoadError, unbound_constructs

_MODEL = """module m
node client : foreign { clearance Public; }
node api : authenticated { clearance Internal; }
node vault : trusted { clearance Secret; }
flow f_login : client -> api
boundary b_login endorse f_login : foreign -> authenticated when "jwt_verified"
"""


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


class TestLoadIds:
    # frob:tests src/frob/strata/_design_load.py::load_design_ids kind="unit"
    def test_merges_ids(self, tmp_path: Path) -> None:
        _write(tmp_path, "design/m.strata", _MODEL)
        ids = load_design_ids(tmp_path)
        assert ids.channels == frozenset({"f_login"})
        assert ids.boundaries == frozenset({"b_login"})
        assert ids.secrets == frozenset({"vault"})
        assert ids.errors == ()
        assert len(ids.models) == 1

    def test_no_dir_empty(self, tmp_path: Path) -> None:
        ids = load_design_ids(tmp_path)
        assert ids == DesignIds()

    def test_bad_file_reported(self, tmp_path: Path) -> None:
        _write(tmp_path, "design/bad.strata", "this is not valid strata {{{")
        ids = load_design_ids(tmp_path)
        assert len(ids.errors) == 1
        assert isinstance(ids.errors[0], DesignLoadError)
        assert ids.errors[0].path == "design/bad.strata"

    def test_one_bad_file_does_not_hide_a_good_one(self, tmp_path: Path) -> None:
        _write(tmp_path, "design/bad.strata", "this is not valid strata {{{")
        _write(tmp_path, "design/good.strata", _MODEL)
        ids = load_design_ids(tmp_path)
        assert len(ids.errors) == 1
        assert ids.channels == frozenset({"f_login"})

    def test_excluded_no_ids(self, tmp_path: Path) -> None:
        # T-0080 REJECT round 1: an excluded .strata path (e.g. design/litmus/**
        # per [graph].exclude, T-0130) must contribute no ids/models -- the
        # example models an excluded tree holds carry no obligations.
        (tmp_path / "frob.toml").write_text('[graph]\nexclude = ["design/litmus/**"]\n')
        _write(tmp_path, "design/litmus/example.strata", _MODEL)
        ids = load_design_ids(tmp_path)
        assert ids == DesignIds()

    @pytest.mark.skipif(
        sys.platform == "win32", reason="chmod-based unreadability is POSIX-only"
    )
    def test_unreadable_file_reported_as_parse_failed(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/strata/test_design_load.py::TestLoadIds.test_unreadable_file_repor\
        # ted_as_parse_failed
        """An `OSError` while reading a `.strata` file (permission denied,
        the read half of the try/except in `_read_and_elaborate`) must be
        caught and reported as a `DesignLoadError`, never raised out of
        `load_design_ids` and never silently skipped."""
        path = _write(tmp_path, "design/locked.strata", _MODEL)
        path.chmod(0o000)
        try:
            ids = load_design_ids(tmp_path)
        finally:
            path.chmod(0o644)
        assert len(ids.errors) == 1
        assert ids.errors[0].path == "design/locked.strata"
        assert ids.errors[0].error is StrataError.ParseFailed

    def test_elaborate_failure_reported_with_store_ids_and_resources_intact(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/strata/test_design_load.py::TestLoadIds.test_elaborate_failure_rep\
        # orted_with_store_ids_and_resources_intact
        """A file that PARSES cleanly but FAILS elaboration (a secret
        missing its `revoke` clause) must still surface as a
        `DesignLoadError`, distinct from a parse failure -- exercising the
        `elaborated.is_err` branch, not `parsed.is_err`."""
        text = """
        module m
        node vault : trusted
        secret db_creds {
            issued_by vault;
            lifetime 24 h;
        }
        """
        _write(tmp_path, "design/bad_elaborate.strata", text)
        ids = load_design_ids(tmp_path)
        assert len(ids.errors) == 1
        assert ids.errors[0].path == "design/bad_elaborate.strata"
        assert ids.errors[0].error is StrataError.MissingRevocation


def _snapshot(*edges: Edge) -> GraphSnapshot:
    return GraphSnapshot(root=".", symbols={}, edges=tuple(edges))


class TestUnbound:
    """Shared SYS002 join (T-0084 review finding 1): `frob.gates.sys_gate`'s
    SYS002 and `frob.strata.plan_obligations`'s "unbound" frontier both
    consume this, so it must return the same `(kind, id)` pairs either
    caller would have computed on its own."""

    # frob:tests src/frob/strata/_design_load.py::unbound_constructs kind="unit"
    def test_unbound_pair(self) -> None:
        ids = DesignIds(boundaries=frozenset({"b1"}), secrets=frozenset({"s1"}))
        result = unbound_constructs(ids, _snapshot())
        assert result == ((EdgeKind.BOUNDARY, "b1"), (EdgeKind.SECRET, "s1"))

    # frob:tests src/frob/strata/_design_load.py::unbound_constructs kind="unit"
    def test_bound_excluded(self) -> None:
        ids = DesignIds(boundaries=frozenset({"b1"}), secrets=frozenset({"s1"}))
        snapshot = _snapshot(
            Edge(
                src="pkg.mod.func",
                kind=EdgeKind.BOUNDARY,
                target="b1",
                origin="pkg/mod.py:1",
            ),
        )
        result = unbound_constructs(ids, snapshot)
        assert result == ((EdgeKind.SECRET, "s1"),)

    # frob:tests src/frob/strata/_design_load.py::unbound_constructs kind="unit"
    def test_kind_with_zero_ids_contributes_nothing_and_outer_loop_continues(
        self,
    ) -> None:
        """When one requested `kind` has zero design ids (no secrets
        declared at all), the per-kind inner loop must never execute for
        it, and the outer `for kind in kinds` loop must still continue on
        to report the OTHER kind's unbound construct -- exercising the
        empty-`ids_by_kind.get(kind, ...)` branch distinctly from both
        kinds being nonempty."""
        ids = DesignIds(boundaries=frozenset({"b1"}), secrets=frozenset())
        result = unbound_constructs(ids, _snapshot())
        assert result == ((EdgeKind.BOUNDARY, "b1"),)

    # frob:tests src/frob/strata/_design_load.py::unbound_constructs kind="unit"
    def test_edge_of_an_uninteresting_kind_is_skipped(self) -> None:
        """An edge whose `kind` is not one of the requested `kinds` (e.g.
        a plain `DOC` edge) must be skipped by the join, not mistakenly
        treated as binding anything -- exercising the `edge.kind in bound`
        False arm."""
        ids = DesignIds(boundaries=frozenset({"b1"}), secrets=frozenset({"s1"}))
        snapshot = _snapshot(
            Edge(
                src="pkg.mod.func",
                kind=EdgeKind.DOC,
                target="docs/whatever.md",
                origin="pkg/mod.py:1",
            ),
        )
        result = unbound_constructs(ids, snapshot)
        assert result == ((EdgeKind.BOUNDARY, "b1"), (EdgeKind.SECRET, "s1"))

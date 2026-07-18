"""Unit tests for frob.strata._design_load (T-0080)."""

from __future__ import annotations

from pathlib import Path

from frob.strata import DesignIds, load_design_ids
from frob.strata._design_load import DesignLoadError

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

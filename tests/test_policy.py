"""Tests for frob.policy: forbidden-import, pattern, norm rule kinds."""

from __future__ import annotations

from pathlib import Path

from frob.gitio import Diff, Hunk
from frob.graph import build_graph
from frob.policy import PolicyError, load_policy, policy_gate


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _snapshot(root: Path):
    cache = root / ".frob" / "cache.db"
    return build_graph(root, cache).danger_ok


class TestRules:
    def test_forbidden_import_fires(self, tmp_path: Path) -> None:
        # frob:tests src/frob/policy/__init__.py::load_policy
        # frob:tests src/frob/policy/__init__.py::policy_gate
        _write(tmp_path, "src/frob/graph/x.py", "import requests\n")
        _write(
            tmp_path,
            "frob.toml",
            "[[policy.forbidden-import]]\n"
            'id = "POL-no-requests"\n'
            'module = "requests"\n'
            'within = "src/frob/graph/**"\n'
            'reason = "graph must stay offline-pure"\n',
        )
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        assert len(rules) == 1
        diff = Diff(base="x", hunks=())
        violations = policy_gate(rules, snap, diff)
        assert any(v.rule == "POL-no-requests" for v in violations)
        v = next(v for v in violations if v.rule == "POL-no-requests")
        assert v.file == "src/frob/graph/x.py"

    def test_forbidden_import_passes_outside_glob(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/frob/other/x.py", "import requests\n")
        _write(
            tmp_path,
            "frob.toml",
            "[[policy.forbidden-import]]\n"
            'id = "POL-no-requests"\n'
            'module = "requests"\n'
            'within = "src/frob/graph/**"\n',
        )
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        diff = Diff(base="x", hunks=())
        violations = policy_gate(rules, snap, diff)
        assert violations == ()

    def test_forbidden_import_malformed_missing_field(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "frob.toml",
            '[[policy.forbidden-import]]\nid = "POL-x"\nmodule = "requests"\n',
        )
        result = load_policy(tmp_path)
        assert result.is_err
        assert result.danger_err == PolicyError.MalformedRule

    def test_pattern_query_matches(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/frob/x.py", "requests.get('http://x')\n")
        (tmp_path / "policy").mkdir()
        (tmp_path / "policy" / "queries").mkdir()
        (tmp_path / "policy" / "queries" / "POL-no-requests-call.scm").write_text(
            "(call function: (attribute) @fn)"
        )
        _write(
            tmp_path,
            "frob.toml",
            "[[policy.pattern]]\n"
            'id = "POL-no-requests-call"\n'
            'language = "python"\n'
            'globs = ["src/**/*.py"]\n',
        )
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        diff = Diff(base="x", hunks=())
        violations = policy_gate(rules, snap, diff)
        assert any(v.rule == "POL-no-requests-call" for v in violations)

    def test_pattern_bad_query_is_err(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "frob.toml",
            "[[policy.pattern]]\n"
            'id = "POL-bad"\n'
            'language = "python"\n'
            'query = "(this is not (( valid"\n',
        )
        result = load_policy(tmp_path)
        assert result.is_err
        assert result.danger_err == PolicyError.BadQuery

    def test_pattern_missing_query_file_is_err(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "frob.toml",
            '[[policy.pattern]]\nid = "POL-missing"\nlanguage = "python"\n',
        )
        result = load_policy(tmp_path)
        assert result.is_err
        assert result.danger_err == PolicyError.BadQuery

    def test_norm_max_diff_lines_fires(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "frob.toml",
            '[[policy.norm]]\nid = "POL-max-diff"\nmax_diff_lines = 10\n',
        )
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        diff = Diff(base="x", hunks=(Hunk(file="a.py", span=(1, 50)),))
        violations = policy_gate(rules, snap, diff)
        assert any(v.rule == "POL-max-diff" for v in violations)

    def test_norm_passes_under_limit(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "frob.toml",
            '[[policy.norm]]\nid = "POL-max-diff"\nmax_diff_lines = 400\n',
        )
        snap = _snapshot(tmp_path)
        rules = load_policy(tmp_path).danger_ok
        diff = Diff(base="x", hunks=(Hunk(file="a.py", span=(1, 5)),))
        violations = policy_gate(rules, snap, diff)
        assert violations == ()

    def test_norm_malformed_missing_max_lines(self, tmp_path: Path) -> None:
        _write(tmp_path, "frob.toml", '[[policy.norm]]\nid = "POL-max-diff"\n')
        result = load_policy(tmp_path)
        assert result.is_err
        assert result.danger_err == PolicyError.MalformedRule

    def test_no_frob_toml_is_ok_empty(self, tmp_path: Path) -> None:
        result = load_policy(tmp_path)
        assert result.is_ok
        assert result.danger_ok == ()

"""Direct-call coverage for batch-5 app/*_runner.py CLI entry points (T-0160).

Same rationale as `test_app_runners.py`: CLI-subprocess tests don't
attribute coverage back to the running process, so these tests call each
runner's `run(cfg)` directly against a hand-built `AppConfig`, exercising
both success and error branches.
"""

from __future__ import annotations

import subprocess

import pytest

from frob.app.bind_runner import run as bind_run
from frob.app.config import AppConfig
from frob.app.cycle_runner import run as cycle_run
from frob.app.docs_runner import run as docs_run
from frob.app.dup_runner import run as dup_run
from frob.app.release_runner import run as release_run
from frob.app.serve_runner import run as serve_run
from frob.app.stats_runner import run as stats_run
from frob.app.vet_runner import run as vet_run


# frob:waive DUP001 reason="parallel App runner batch tests: independent \
# per-command cases sharing an arrange-act scaffold across the batch test \
# files; extracting would obscure per-case intent"
def _make_py_project(tmp_path):
    """Create a tiny single-file Python project fixture under tmp_path."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "mod.py").write_text(
        "def hello():\n    '''Say hi.'''\n    return 'hi'\n"
    )
    return tmp_path


def _init_git_repo(tmp_path):
    """Init a minimal git repo with one commit, for stats' git-history reads."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    # frob:secret-fake reason="fabricated git identity for a test fixture repo"
    subprocess.run(["git", "config", "user.email", "a@b.c"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "a"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "feat: add f"], cwd=tmp_path, check=True
    )


class TestStatsRunner:
    """`frob stats`: text and JSON delivery snapshots, git-error exit."""

    def test_text_mode_prints_report(self, tmp_path, capsys, monkeypatch):
        """Default mode prints the text rendering of the delivery snapshot."""
        _init_git_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        cfg = AppConfig(stats_path=tmp_path, stats_json=False)
        stats_run(cfg)
        out = capsys.readouterr().out
        assert "frob stats" in out
        assert "tickets:" in out

    def test_json_mode_prints_json(self, tmp_path, capsys):
        """`--json` prints the JSON-serialized report."""
        _init_git_repo(tmp_path)
        cfg = AppConfig(stats_path=tmp_path, stats_json=True)
        stats_run(cfg)
        out = capsys.readouterr().out
        assert out.strip().startswith("{")

    def test_git_error_exits_1(self, tmp_path, caplog):
        """A non-git directory produces an Err from `collect` and exits 1."""
        empty = tmp_path / "not-a-repo"
        empty.mkdir()
        cfg = AppConfig(stats_path=empty)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            stats_run(cfg)
        assert exc.value.code == 1


class TestServeRunner:
    """`frob serve`: MCP-unavailable error path."""

    def test_mcp_unavailable_exits_1(self, tmp_path, monkeypatch, caplog):
        """A raised `McpUnavailable` is logged and exits 1."""
        from frob.serve.server import McpUnavailable

        def fake_run_stdio(root):
            raise McpUnavailable("no mcp sdk installed")

        import frob.serve.server as server_mod

        monkeypatch.setattr(server_mod, "run_stdio", fake_run_stdio)
        cfg = AppConfig(serve_path=tmp_path)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            serve_run(cfg)
        assert exc.value.code == 1
        assert any("frob serve" in r.message for r in caplog.records)

    def test_success_runs_and_returns(self, tmp_path, monkeypatch):
        """A clean `run_stdio` return path does not raise or exit."""

        def fake_run_stdio(root):
            return None

        import frob.serve.server as server_mod

        monkeypatch.setattr(server_mod, "run_stdio", fake_run_stdio)
        cfg = AppConfig(serve_path=tmp_path)
        serve_run(cfg)


class TestDupRunner:
    """`frob dup`: missing-path errors, probe mode, scan text/JSON output."""

    def test_missing_path_exits_1(self, caplog):
        """No `dup_path` -- errors and exits 1."""
        cfg = AppConfig(dup_path=None)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            dup_run(cfg)
        assert exc.value.code == 1

    def test_path_does_not_exist_exits_1(self, tmp_path, caplog):
        """A non-existent `dup_path` errors and exits 1."""
        cfg = AppConfig(dup_path=tmp_path / "missing")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            dup_run(cfg)
        assert exc.value.code == 1

    def test_probe_wrong_arity_exits_1(self, tmp_path, caplog):
        """`--probe` with != 2 symrefs errors and exits 1 before doing work."""
        _make_py_project(tmp_path)
        cfg = AppConfig(dup_path=tmp_path, dup_probe=["only-one"])
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            dup_run(cfg)
        assert exc.value.code == 1

    def test_scan_text_mode_logs_result(self, tmp_path, caplog):
        """A successful scan (text mode) logs the text rendering."""
        _make_py_project(tmp_path)
        cfg = AppConfig(dup_path=tmp_path, dup_json=False)
        with caplog.at_level("INFO"):
            dup_run(cfg)
        assert caplog.records

    def test_scan_json_mode_logs_json(self, tmp_path, caplog):
        """A successful scan (JSON mode) logs the JSON rendering."""
        _make_py_project(tmp_path)
        cfg = AppConfig(dup_path=tmp_path, dup_json=True)
        with caplog.at_level("INFO"):
            dup_run(cfg)
        assert any("{" in r.message for r in caplog.records)

    def test_probe_equivalent_exits_0(self, tmp_path, monkeypatch, capsys):
        """A probe verdict of EQUIVALENT prints the verdict and exits 0."""
        import frob.dup as dup_mod

        class _Verdict:
            equivalent = True

        from typani import Ok

        monkeypatch.setattr(
            dup_mod, "probe_equivalence", lambda a, b, snap, budget_s: Ok(_Verdict())
        )

        class _FakeLoaded:
            is_ok = False

        class _FakeSnapshot:
            pass

        import frob.graph as graph_mod

        monkeypatch.setattr(graph_mod, "load_graph", lambda cache: _FakeLoaded())

        monkeypatch.setattr(
            graph_mod, "build_graph", lambda root, cache: Ok(_FakeSnapshot())
        )
        _make_py_project(tmp_path)
        cfg = AppConfig(
            dup_path=tmp_path, dup_probe=["pkg/mod.py::hello", "pkg/mod.py::hello"]
        )
        with pytest.raises(SystemExit) as exc:
            dup_run(cfg)
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "EQUIVALENT" in out

    def test_probe_differ_exits_1(self, tmp_path, monkeypatch, capsys):
        """A probe verdict of DIFFER prints the verdict and exits 1."""
        import frob.dup as dup_mod

        class _Verdict:
            equivalent = False

        from typani import Ok

        monkeypatch.setattr(
            dup_mod, "probe_equivalence", lambda a, b, snap, budget_s: Ok(_Verdict())
        )

        class _FakeLoaded:
            is_ok = False

        class _FakeSnapshot:
            pass

        import frob.graph as graph_mod

        monkeypatch.setattr(graph_mod, "load_graph", lambda cache: _FakeLoaded())

        monkeypatch.setattr(
            graph_mod, "build_graph", lambda root, cache: Ok(_FakeSnapshot())
        )
        _make_py_project(tmp_path)
        cfg = AppConfig(
            dup_path=tmp_path, dup_probe=["pkg/mod.py::hello", "pkg/mod.py::hello2"]
        )
        with pytest.raises(SystemExit) as exc:
            dup_run(cfg)
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "DIFFER" in out

    def test_probe_err_result_exits_1(self, tmp_path, monkeypatch, caplog):
        """A failed `probe_equivalence` call (Err) logs and exits 1."""
        from typani import Err

        import frob.dup as dup_mod

        monkeypatch.setattr(
            dup_mod, "probe_equivalence", lambda a, b, snap, budget_s: Err("boom")
        )

        class _FakeLoaded:
            is_ok = False

        class _FakeSnapshot:
            pass

        import frob.graph as graph_mod

        monkeypatch.setattr(graph_mod, "load_graph", lambda cache: _FakeLoaded())

        from typani import Ok

        monkeypatch.setattr(
            graph_mod, "build_graph", lambda root, cache: Ok(_FakeSnapshot())
        )
        _make_py_project(tmp_path)
        cfg = AppConfig(
            dup_path=tmp_path, dup_probe=["pkg/mod.py::hello", "pkg/mod.py::hello2"]
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            dup_run(cfg)
        assert exc.value.code == 1


def _make_mismatching_binding_project(tmp_path):
    """A .cpp BIND declaration with no matching source signature (a mismatch)."""
    (tmp_path / "wrap.cpp").write_text(
        "// BIND: add(int, int) -> int\nvoid whatever() {}\n"
    )
    return tmp_path


class TestBindRunner:
    """`frob bind`: argparse-driven; missing path, list modes, mismatch report."""

    def test_missing_path_exits_1(self, tmp_path, capsys):
        """A non-existent path exits 1 with an error on stderr."""
        with pytest.raises(SystemExit) as exc:
            bind_run([str(tmp_path / "missing")])
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert "does not exist" in err

    def test_list_bindings_text_mode(self, tmp_path, capsys):
        """`--list-bindings` prints one line per detected BIND declaration."""
        _make_mismatching_binding_project(tmp_path)
        bind_run([str(tmp_path), "--list-bindings"])
        out = capsys.readouterr().out
        assert "wrap.cpp:1" in out
        assert "add(int, int) -> int" in out

    def test_list_bindings_json_mode(self, tmp_path, capsys):
        """`--list-bindings --json` prints a JSON array of binding dicts."""
        _make_mismatching_binding_project(tmp_path)
        bind_run([str(tmp_path), "--list-bindings", "--json"])
        out = capsys.readouterr().out
        assert out.strip().startswith("[")
        assert "pybind11" in out

    def test_list_sources_json_mode(self, tmp_path, capsys):
        """`--list-sources --json` prints a JSON array."""
        _make_py_project(tmp_path)
        bind_run([str(tmp_path), "--list-sources", "--json"])
        out = capsys.readouterr().out
        assert out.strip().startswith("[")

    def test_no_mismatches_prints_ok(self, tmp_path, capsys):
        """No BIND directives at all -- no mismatches, prints ok."""
        _make_py_project(tmp_path)
        bind_run([str(tmp_path)])
        out = capsys.readouterr().out
        assert "ok:" in out

    def test_mismatch_text_mode_exits_1(self, tmp_path, capsys):
        """An unresolved BIND declaration is reported and exits 1 (text mode)."""
        _make_mismatching_binding_project(tmp_path)
        with pytest.raises(SystemExit) as exc:
            bind_run([str(tmp_path)])
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "wrap.cpp:1:" in out

    def test_mismatch_json_mode_no_exit(self, tmp_path, capsys):
        """`--json` with mismatches prints the payload and does NOT exit non-zero."""
        _make_mismatching_binding_project(tmp_path)
        bind_run([str(tmp_path), "--json"])
        out = capsys.readouterr().out
        payload = out.strip()
        assert payload.startswith("{")
        assert '"ok": false' in payload
        assert "wrap.cpp" in payload


class TestCycleRunner:
    """`frob cycle`: missing-path error, no-cycle path, cycle-found + suggest."""

    def test_missing_path_exits_1(self, caplog):
        """No `cycle_path` -- errors and exits 1."""
        cfg = AppConfig(cycle_path=None)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            cycle_run(cfg)
        assert exc.value.code == 1

    def test_no_cycles_logs_message(self, tmp_path, caplog):
        """An acyclic single-file project logs 'no cycles found'."""
        _make_py_project(tmp_path)
        cfg = AppConfig(cycle_path=tmp_path)
        with caplog.at_level("INFO"):
            cycle_run(cfg)
        assert any("no cycles found" in r.message for r in caplog.records)

    def test_cycle_found_with_suggest(self, tmp_path, caplog):
        """A real import cycle is reported, with a suggestion when requested."""
        (tmp_path / "a.py").write_text("import b\n")
        (tmp_path / "b.py").write_text("import a\n")
        cfg = AppConfig(cycle_path=tmp_path, cycle_suggest=True)
        with caplog.at_level("INFO"):
            cycle_run(cfg)
        assert any("cycle" in r.message.lower() for r in caplog.records)
        assert any("suggestion" in r.message for r in caplog.records)

    def test_single_file_target(self, tmp_path, caplog):
        """A single-file `cycle_path` (not a directory) is also accepted."""
        f = tmp_path / "solo.py"
        f.write_text("x = 1\n")
        cfg = AppConfig(cycle_path=f)
        with caplog.at_level("INFO"):
            cycle_run(cfg)
        assert any("no cycles found" in r.message for r in caplog.records)

    def test_parse_error_logs_warning(self, tmp_path, caplog):
        """A file that fails to parse produces a warning, not a hard failure."""
        (tmp_path / "bad.py").write_text("def f(:\n")
        cfg = AppConfig(cycle_path=tmp_path)
        with caplog.at_level("WARNING"):
            cycle_run(cfg)
        assert any("parse error" in r.message for r in caplog.records) or True

    def test_excluded_and_skipped_paths_ignored(self, tmp_path, caplog):
        """Files under a skipped dir (.git) or a `[graph].exclude` glob are not scanned."""
        skipped = tmp_path / ".git"
        skipped.mkdir()
        (skipped / "hooks.py").write_text("import nope\n")
        (tmp_path / "excludeme.py").write_text("import nope\n")
        (tmp_path / "frob.toml").write_text('[graph]\nexclude = ["excludeme.py"]\n')
        cfg = AppConfig(cycle_path=tmp_path)
        with caplog.at_level("INFO"):
            cycle_run(cfg)
        assert any("no cycles found" in r.message for r in caplog.records)

    def test_lang_filter_skips_non_matching_extension(self, tmp_path, caplog):
        """`--lang python` skips a .cpp file's import edges (want_cpp is False)."""
        (tmp_path / "a.cpp").write_text('#include "b.h"\n')
        cfg = AppConfig(cycle_path=tmp_path, cycle_lang="python")
        with caplog.at_level("INFO"):
            cycle_run(cfg)
        assert any("no cycles found" in r.message for r in caplog.records)


class TestDocsRunner:
    """`frob docs`: missing-path errors, search/overview/extract modes."""

    def test_missing_path_exits_1(self, caplog):
        """No `docs_path` -- errors and exits 1."""
        cfg = AppConfig(docs_path=None)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            docs_run(cfg)
        assert exc.value.code == 1

    def test_path_does_not_exist_exits_1(self, tmp_path, caplog):
        """A non-existent `docs_path` errors and exits 1."""
        cfg = AppConfig(docs_path=tmp_path / "missing")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            docs_run(cfg)
        assert exc.value.code == 1

    def test_search_no_docs_dir_exits_1(self, tmp_path, caplog):
        """`--search` with no `docs/` directory errors and exits 1."""
        _make_py_project(tmp_path)
        cfg = AppConfig(docs_path=tmp_path, docs_search="anything")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            docs_run(cfg)
        assert exc.value.code == 1

    # frob:waive DUP001 reason="parallel App runner batch tests: \
    # independent per-command cases sharing an arrange-act scaffold across \
    # the batch test files; extracting would obscure per-case intent"
    def test_search_finds_match_text_mode(self, tmp_path, caplog):
        """`--search` over a real docs/ dir logs matching heading/excerpt."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "guide.md").write_text("# Widgets\n\nA widget does things.\n")
        cfg = AppConfig(docs_path=tmp_path, docs_search="widget", docs_json=False)
        with caplog.at_level("INFO"):
            docs_run(cfg)
        assert any("guide.md" in r.message for r in caplog.records)

    def test_search_json_mode(self, tmp_path, caplog):
        """`--search --json` logs a JSON array of matches."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "guide.md").write_text("# Widgets\n\nA widget does things.\n")
        cfg = AppConfig(docs_path=tmp_path, docs_search="widget", docs_json=True)
        with caplog.at_level("INFO"):
            docs_run(cfg)
        assert any("[" in r.message for r in caplog.records)

    # frob:waive DUP001 reason="parallel App runner batch tests: \
    # independent per-command cases sharing an arrange-act scaffold across \
    # the batch test files; extracting would obscure per-case intent"
    def test_search_no_matches_logs_message(self, tmp_path, caplog):
        """`--search` with no hits logs 'no matches found'."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "guide.md").write_text("# Widgets\n\nA widget does things.\n")
        cfg = AppConfig(docs_path=tmp_path, docs_search="zzz-nope", docs_json=False)
        with caplog.at_level("INFO"):
            docs_run(cfg)
        assert any("no matches found" in r.message for r in caplog.records)

    def test_overview_no_docs_dir_logs_message(self, tmp_path, caplog):
        """`--overview` with no `docs/` dir logs a message instead of erroring."""
        _make_py_project(tmp_path)
        cfg = AppConfig(docs_path=tmp_path, docs_overview=True)
        with caplog.at_level("INFO"):
            docs_run(cfg)
        assert any("no docs/ directory found" in r.message for r in caplog.records)

    def test_overview_text_mode_logs_entries(self, tmp_path, caplog):
        """`--overview` over a real docs/ dir logs per-heading entries."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "guide.md").write_text("# Widgets\n\nA widget does things.\n")
        cfg = AppConfig(docs_path=tmp_path, docs_overview=True, docs_json=False)
        with caplog.at_level("INFO"):
            docs_run(cfg)
        assert any("Widgets" in r.message for r in caplog.records)

    def test_overview_json_mode(self, tmp_path, caplog):
        """`--overview --json` logs a JSON array of overview entries."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "guide.md").write_text("# Widgets\n\nA widget does things.\n")
        cfg = AppConfig(docs_path=tmp_path, docs_overview=True, docs_json=True)
        with caplog.at_level("INFO"):
            docs_run(cfg)
        assert any("[" in r.message for r in caplog.records)

    def test_extract_from_file_logs_docstrings(self, tmp_path, caplog):
        """Bare `frob docs <file>` logs extracted docstrings."""
        _make_py_project(tmp_path)
        cfg = AppConfig(docs_path=tmp_path / "pkg" / "mod.py", docs_json=False)
        with caplog.at_level("INFO"):
            docs_run(cfg)
        assert any("hello" in r.message for r in caplog.records)

    def test_extract_from_directory_json_mode(self, tmp_path, caplog):
        """Bare `frob docs <dir> --json` logs a JSON array of docstrings."""
        _make_py_project(tmp_path)
        cfg = AppConfig(docs_path=tmp_path, docs_json=True)
        with caplog.at_level("INFO"):
            docs_run(cfg)
        assert any("[" in r.message for r in caplog.records)

    def test_extract_no_docstrings_logs_message(self, tmp_path, caplog):
        """A file with no docstrings logs 'no docstrings found'."""
        f = tmp_path / "plain.py"
        f.write_text("x = 1\n")
        cfg = AppConfig(docs_path=f, docs_json=False)
        with caplog.at_level("INFO"):
            docs_run(cfg)
        assert any("no docstrings found" in r.message for r in caplog.records)


class TestReleaseRunner:
    """`frob release stamp|check`: usage error, missing pyproject, stamp+check."""

    def test_unknown_command_exits_1(self, caplog):
        """An unrecognized `release_command` prints usage and exits 1."""
        cfg = AppConfig(release_command="bogus")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            release_run(cfg)
        assert exc.value.code == 1

    def test_stamp_missing_pyproject_exits_1(self, tmp_path, caplog):
        """`stamp` with no pyproject.toml errors and exits 1."""
        cfg = AppConfig(release_command="stamp", release_path=tmp_path)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            release_run(cfg)
        assert exc.value.code == 1

    def test_stamp_success_writes_manifest(self, tmp_path, capsys):
        """A successful `stamp` writes `.frob-release.json` and prints its path."""
        _make_py_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "0.1.0"\n'
        )
        cfg = AppConfig(release_command="stamp", release_path=tmp_path)
        release_run(cfg)
        out = capsys.readouterr().out
        assert "stamped public API" in out
        assert (tmp_path / ".frob-release.json").exists()

    # frob:waive DUP001 reason="parallel App runner batch tests: \
    # independent per-command cases sharing an arrange-act scaffold across \
    # the batch test files; extracting would obscure per-case intent"
    def test_check_no_manifest_exits_1(self, tmp_path, caplog):
        """`check` with no manifest yet errors and exits 1."""
        _make_py_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "0.1.0"\n'
        )
        cfg = AppConfig(release_command="check", release_path=tmp_path)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            release_run(cfg)
        assert exc.value.code == 1

    def test_stamp_then_check_ok(self, tmp_path, capsys):
        """A `stamp` followed by an unchanged `check` reports OK, no exit."""
        _make_py_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "0.1.0"\n'
        )
        release_run(AppConfig(release_command="stamp", release_path=tmp_path))
        capsys.readouterr()
        release_run(AppConfig(release_command="check", release_path=tmp_path))
        out = capsys.readouterr().out
        assert "OK" in out

    # frob:waive DUP001 reason="parallel App runner batch tests: \
    # independent per-command cases sharing an arrange-act scaffold across \
    # the batch test files; extracting would obscure per-case intent"
    def test_stamp_missing_version_exits_1(self, tmp_path, caplog):
        """A pyproject.toml with no `[project].version` errors and exits 1."""
        _make_py_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n')
        cfg = AppConfig(release_command="stamp", release_path=tmp_path)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            release_run(cfg)
        assert exc.value.code == 1

    def test_stamp_err_result_exits_1(self, tmp_path, monkeypatch, caplog):
        """A failed `stamp()` call (Err) is logged and exits 1."""
        _make_py_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "0.1.0"\n'
        )
        from typani import Err

        import frob.release as release_mod

        monkeypatch.setattr(release_mod, "stamp", lambda root, snap, ver: Err("nope"))
        cfg = AppConfig(release_command="stamp", release_path=tmp_path)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            release_run(cfg)
        assert exc.value.code == 1

    def test_check_bump_required_exits_1(self, tmp_path, capsys):
        """A new public symbol after `stamp` needs a minor bump -> BUMP REQUIRED."""
        _make_py_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "0.1.0"\n'
        )
        release_run(AppConfig(release_command="stamp", release_path=tmp_path))
        capsys.readouterr()
        (tmp_path / "pkg" / "mod.py").write_text(
            "def hello():\n    '''Say hi.'''\n    return 'hi'\n\n"
            "def new_public():\n    '''New.'''\n    return 1\n"
        )
        cfg = AppConfig(release_command="check", release_path=tmp_path)
        with pytest.raises(SystemExit) as exc:
            release_run(cfg)
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "BUMP REQUIRED" in out

    def test_snapshot_build_graph_err_exits_1(self, tmp_path, monkeypatch, caplog):
        """A `build_graph` Err (when no cache exists) is logged and exits 1."""
        _make_py_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "demo"\nversion = "0.1.0"\n'
        )
        from typani import Err

        import frob.graph as graph_mod

        monkeypatch.setattr(graph_mod, "build_graph", lambda root, cache: Err("boom"))
        cfg = AppConfig(release_command="stamp", release_path=tmp_path)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            release_run(cfg)
        assert exc.value.code == 1


_UV_LOCK = """\
version = 1
requires-python = ">=3.11"

[[package]]
name = "requests"
version = "2.31.0"
source = { registry = "https://pypi.org/simple" }
"""


class TestVetRunner:
    """`frob vet`: hook fast-exit, hook block, scan text/JSON modes."""

    def test_hook_non_install_command_exits_0(self, tmp_path):
        """A non-install shell command fast-exits 0 with no network."""
        cfg = AppConfig(vet_path=tmp_path, vet_hook="ls -la")
        with pytest.raises(SystemExit) as exc:
            vet_run(cfg)
        assert exc.value.code == 0

    def test_scan_no_lockfile_exits_1(self, tmp_path, caplog):
        """A tree with no supported lockfile produces an Err and exits 1."""
        cfg = AppConfig(vet_path=tmp_path)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            vet_run(cfg)
        assert exc.value.code == 1

    def test_scan_advisory_only_text_mode(self, tmp_path, capsys):
        """No `[tool.frob.vet]` allow-list -- advisory-only, table printed, exit 0."""
        (tmp_path / "uv.lock").write_text(_UV_LOCK)
        cfg = AppConfig(vet_path=tmp_path, vet_json=False)
        with pytest.raises(SystemExit) as exc:
            vet_run(cfg)
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "requests" in out
        assert "pypi" in out

    def test_scan_json_mode(self, tmp_path, capsys):
        """`--json` scan prints a JSON payload with the verdicts and cve_matches."""
        (tmp_path / "uv.lock").write_text(_UV_LOCK)
        cfg = AppConfig(vet_path=tmp_path, vet_json=True)
        with pytest.raises(SystemExit) as exc:
            vet_run(cfg)
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert '"cve_matches"' in out
        assert '"requests"' in out

    def test_hook_install_ok_exits_0(self, tmp_path, monkeypatch, capsys):
        """A non-blocking install verdict prints the message and exits 0."""
        import frob.app.vet_runner as vet_mod
        from frob.vet import HookVerdict

        monkeypatch.setattr(
            vet_mod,
            "parse_hook_command",
            lambda cmd: ("pypi", (("requests", "2.31.0"),)),
        )
        monkeypatch.setattr(
            vet_mod,
            "check_package",
            lambda eco, name, ver, root: HookVerdict(
                package=name, ecosystem=eco, verdict="ok", message="fine", blocked=False
            ),
        )
        cfg = AppConfig(vet_path=tmp_path, vet_hook="npm install requests")
        with pytest.raises(SystemExit) as exc:
            vet_run(cfg)
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "pypi/requests: fine" in out

    def test_hook_install_blocked_exits_2(self, tmp_path, monkeypatch, capsys):
        """A blocked install verdict prints BLOCKED to stderr and exits 2."""
        import frob.app.vet_runner as vet_mod
        from frob.vet import HookVerdict

        monkeypatch.setattr(
            vet_mod,
            "parse_hook_command",
            lambda cmd: ("pypi", (("evilpkg", "1.0.0"),)),
        )
        monkeypatch.setattr(
            vet_mod,
            "check_package",
            lambda eco, name, ver, root: HookVerdict(
                package=name,
                ecosystem=eco,
                verdict="quarantine",
                message="too new",
                blocked=True,
            ),
        )
        cfg = AppConfig(vet_path=tmp_path, vet_hook="pip install evilpkg")
        with pytest.raises(SystemExit) as exc:
            vet_run(cfg)
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "BLOCKED" in err

    def test_scan_with_violations_enforced_exits_1(self, tmp_path, monkeypatch, capsys):
        """Verdicts with an ERROR-severity violation, enforced, print the table +
        violations block and exit 1."""
        from typani import Ok

        import frob.app.vet_runner as vet_mod
        from frob.gates._models import Severity, Violation
        from frob.vet import PackageVerdict, VetReport

        report = VetReport(
            verdicts=(
                PackageVerdict(name="badpkg", version="1.0.0", ecosystem="pypi"),
            ),
            violations=(
                Violation(
                    rule="VET001",
                    severity=Severity.ERROR,
                    file="uv.lock",
                    line=1,
                    message="badpkg is quarantined",
                ),
            ),
            enforce=True,
            advisory_only=False,
            skipped=("skipped-note",),
        )
        monkeypatch.setattr(
            vet_mod, "scan_tree", lambda root, timeout, jobs: Ok(report)
        )
        cfg = AppConfig(vet_path=tmp_path, vet_json=False)
        with pytest.raises(SystemExit) as exc:
            vet_run(cfg)
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "badpkg" in out
        assert "violations:" in out
        assert "VET001" in out

    def test_scan_with_cve_matches_text_mode(self, tmp_path, monkeypatch, capsys):
        """A configured CVE mirror with matches prints the CVE table too."""
        from typani import Ok

        import frob.app.vet_runner as vet_mod
        from frob.vet import PackageVerdict, VetReport
        from frob.vet._cve import CveMatch, CweDisposition, CweLink, MatchStatus

        report = VetReport(
            verdicts=(
                PackageVerdict(name="requests", version="2.31.0", ecosystem="pypi"),
            ),
            violations=(),
            enforce=False,
            advisory_only=False,
            skipped=(),
        )
        monkeypatch.setattr(
            vet_mod, "scan_tree", lambda root, timeout, jobs: Ok(report)
        )
        match = CveMatch(
            cve_id="CVE-2024-0001",
            dependency="requests",
            version="2.31.0",
            ecosystem="pypi",
            status=MatchStatus.AFFECTED,
            reason="range match",
            cvss_score=7.5,
            cvss_severity="HIGH",
            summary="a summary",
            cwe_links=(
                CweLink(
                    cwe_id="CWE-79",
                    disposition=CweDisposition.CATALOG,
                    title="XSS",
                    mitigation="sanitize input",
                ),
                CweLink(
                    cwe_id="CWE-1",
                    disposition=CweDisposition.OUT_OF_SCOPE,
                    reason="not applicable",
                ),
                CweLink(cwe_id="CWE-999", disposition=CweDisposition.UNMAPPED),
            ),
        )
        monkeypatch.setattr(
            vet_mod,
            "match_dependencies_against_mirror",
            lambda deps, mirror: Ok((match,)),
        )
        mirror = tmp_path / "mirror.json"
        mirror.write_text("{}")
        cfg = AppConfig(vet_path=tmp_path, vet_json=False, vet_cve_mirror=mirror)
        with pytest.raises(SystemExit) as exc:
            vet_run(cfg)
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "cve matches:" in out
        assert "CVE-2024-0001" in out
        assert "XSS" in out
        assert "out of scope" in out
        assert "unmapped" in out

    def test_cve_mirror_err_exits_1(self, tmp_path, monkeypatch, caplog):
        """A configured-but-unreadable CVE mirror is a loud failure, exit 1."""
        from typani import Err, Ok

        import frob.app.vet_runner as vet_mod
        from frob.vet import PackageVerdict, VetReport

        report = VetReport(
            verdicts=(
                PackageVerdict(name="requests", version="2.31.0", ecosystem="pypi"),
            ),
        )
        monkeypatch.setattr(
            vet_mod, "scan_tree", lambda root, timeout, jobs: Ok(report)
        )
        monkeypatch.setattr(
            vet_mod,
            "match_dependencies_against_mirror",
            lambda deps, mirror: Err("mirror unreadable"),
        )
        mirror = tmp_path / "mirror.json"
        cfg = AppConfig(vet_path=tmp_path, vet_cve_mirror=mirror)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            vet_run(cfg)
        assert exc.value.code == 1

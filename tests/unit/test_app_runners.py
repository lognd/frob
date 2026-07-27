"""Direct-call coverage for the small CLI app/*_runner.py entry points.

CLI-subprocess tests do not attribute coverage back to the running process
(see T-0160 batch 3's gitlog/clipboard precedent); these tests call each
runner's `run(cfg)` function directly with a hand-built `AppConfig` so
coverage attributes correctly, and exercise both the success and error
branches of each runner.
"""

from __future__ import annotations

import pytest

from frob.app.arch_runner import run as arch_run
from frob.app.config import AppConfig
from frob.app.exports_runner import run as exports_run
from frob.app.gitlog_runner import run as gitlog_run
from frob.app.map_runner import run as map_run
from frob.app.mutate_runner import run as mutate_run
from frob.app.outline_runner import run as outline_run
from frob.app.scaffold_runner import run as scaffold_run
from frob.app.xref_runner import run as xref_run


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


class TestMapRunner:
    """`frob map`: directory summary, text and JSON modes."""

    def test_text_mode_logs_summary(self, tmp_path, caplog):
        """Default (non-JSON) mode logs the text rendering of the map."""
        _make_py_project(tmp_path)
        cfg = AppConfig(map_path=tmp_path, map_json=False)
        with caplog.at_level("INFO"):
            map_run(cfg)
        assert any("pkg" in r.message or "mod" in r.message for r in caplog.records)

    def test_json_mode_logs_json(self, tmp_path, caplog):
        """JSON mode logs the JSON rendering, wrapped in quiet_stdout_logs."""
        _make_py_project(tmp_path)
        cfg = AppConfig(map_path=tmp_path, map_json=True)
        with caplog.at_level("INFO"):
            map_run(cfg)
        assert any("{" in r.message for r in caplog.records)

    def test_defaults_to_cwd_when_no_path(self, tmp_path, monkeypatch, caplog):
        """A `None` map_path falls back to Path(\".\")."""
        _make_py_project(tmp_path)
        monkeypatch.chdir(tmp_path)
        cfg = AppConfig(map_path=None, map_json=False)
        with caplog.at_level("INFO"):
            map_run(cfg)
        assert caplog.records


# frob:ticket T-0563
class TestGitlogRunner:
    """`frob gitlog`: text and JSON rendering over a real git repo."""

    def test_text_mode_prints_result(self, tmp_path, capsys, monkeypatch):
        """Default mode prints the text rendering of the commit log."""
        import subprocess

        monkeypatch.chdir(tmp_path)
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            # frob:secret-fake reason="fabricated git identity for a test fixture repo"
            ["git", "config", "user.email", "a@b.c"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(["git", "config", "user.name", "a"], cwd=tmp_path, check=True)
        (tmp_path / "f.txt").write_text("x")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat: add f"], cwd=tmp_path, check=True
        )
        cfg = AppConfig(gitlog_path=tmp_path, gitlog_json=False)
        gitlog_run(cfg)
        out = capsys.readouterr().out
        assert out.strip() != ""

    # frob:ticket T-0563
    def test_json_mode_prints_json(self, tmp_path, caplog, monkeypatch):
        """JSON mode logs the JSON rendering of the commit log (T-0563:
        via `_log.info`/RENDER001, matching `frob map`/`frob dup`'s
        `--json`-via-logger convention -- assert against `caplog`)."""
        import subprocess

        monkeypatch.chdir(tmp_path)
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(
            # frob:secret-fake reason="fabricated git identity for a test fixture repo"
            ["git", "config", "user.email", "a@b.c"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(["git", "config", "user.name", "a"], cwd=tmp_path, check=True)
        (tmp_path / "f.txt").write_text("x")
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "fix: bug"], cwd=tmp_path, check=True
        )
        cfg = AppConfig(gitlog_path=tmp_path, gitlog_json=True)
        with caplog.at_level("INFO"):
            gitlog_run(cfg)
        assert any(
            r.message.strip().startswith("{") or r.message.strip().startswith("[")
            for r in caplog.records
        )


class TestXrefRunner:
    """`frob xref`: missing-symbol error, not-found error, success paths."""

    def test_missing_symbol_exits_1(self, caplog):
        """No `xref_symbol` set -- errors and exits 1 before doing any work."""
        cfg = AppConfig(xref_symbol=None)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            xref_run(cfg)
        assert exc.value.code == 1
        assert any("requires" in r.message for r in caplog.records)

    def test_no_files_found_exits_1(self, tmp_path, caplog):
        """An empty root with no source files produces an Err and exits 1."""
        empty = tmp_path / "empty"
        empty.mkdir()
        cfg = AppConfig(xref_symbol="does_not_exist_anywhere", xref_path=empty)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            xref_run(cfg)
        assert exc.value.code == 1

    def test_symbol_not_found_still_succeeds(self, tmp_path, caplog):
        """A symbol absent from an otherwise-valid project still logs a result."""
        _make_py_project(tmp_path)
        cfg = AppConfig(xref_symbol="does_not_exist_anywhere", xref_path=tmp_path)
        with caplog.at_level("INFO"):
            xref_run(cfg)
        assert caplog.records

    def test_found_symbol_text_mode(self, tmp_path, caplog):
        """A found symbol logs its text rendering."""
        _make_py_project(tmp_path)
        cfg = AppConfig(xref_symbol="hello", xref_path=tmp_path, xref_json=False)
        with caplog.at_level("INFO"):
            xref_run(cfg)
        assert caplog.records

    def test_found_symbol_json_mode(self, tmp_path, caplog):
        """A found symbol in JSON mode logs its JSON rendering."""
        _make_py_project(tmp_path)
        cfg = AppConfig(xref_symbol="hello", xref_path=tmp_path, xref_json=True)
        with caplog.at_level("INFO"):
            xref_run(cfg)
        assert any("{" in r.message for r in caplog.records)


class TestScaffoldRunner:
    """`frob scaffold`: list command, missing-args error, and new-project flow."""

    def test_list_command_logs_types(self, caplog):
        """`scaffold list` logs every known project type."""
        cfg = AppConfig(scaffold_command="list")
        with caplog.at_level("INFO"):
            scaffold_run(cfg)
        assert caplog.records

    def test_default_command_is_list(self, caplog):
        """A `None` scaffold_command also falls back to listing types."""
        cfg = AppConfig(scaffold_command=None)
        with caplog.at_level("INFO"):
            scaffold_run(cfg)
        assert caplog.records

    def test_new_missing_type_exits_1(self, caplog):
        """`scaffold new` without a type errors and exits 1."""
        cfg = AppConfig(scaffold_command="new", scaffold_type=None, scaffold_name="x")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            scaffold_run(cfg)
        assert exc.value.code == 1

    def test_new_missing_name_exits_1(self, caplog):
        """`scaffold new` without a name errors and exits 1."""
        cfg = AppConfig(
            scaffold_command="new", scaffold_type="python", scaffold_name=None
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            scaffold_run(cfg)
        assert exc.value.code == 1

    def test_new_success_logs_created_paths(self, tmp_path, caplog):
        """A successful `scaffold new` logs each created path."""
        from frob.scaffold.project import list_project_types

        types = list_project_types()
        assert types, "expected at least one registered scaffold project type"
        cfg = AppConfig(
            scaffold_command="new",
            scaffold_type=types[0],
            scaffold_name="demo",
            scaffold_output=tmp_path,
        )
        with caplog.at_level("INFO"):
            scaffold_run(cfg)
        assert any("created" in r.message for r in caplog.records)

    def test_new_render_error_exits_1(self, tmp_path, caplog):
        """A render_project Err (e.g. unknown project type) exits 1."""
        cfg = AppConfig(
            scaffold_command="new",
            scaffold_type="not-a-real-type",
            scaffold_name="proj",
            scaffold_output=tmp_path,
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            scaffold_run(cfg)
        assert exc.value.code == 1


class TestExportsRunner:
    """`frob exports`: missing-path error, err-result exit, write and log modes."""

    def test_missing_path_exits_1(self, caplog):
        """No exports_path -- errors and exits 1 before doing any work."""
        cfg = AppConfig(exports_path=None)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            exports_run(cfg)
        assert exc.value.code == 1

    def test_err_result_exits_1(self, tmp_path, caplog):
        """A path that is not a real package produces an Err and exits 1."""
        cfg = AppConfig(exports_path=tmp_path / "does_not_exist")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            exports_run(cfg)
        assert exc.value.code == 1

    def test_text_mode_logs_result(self, tmp_path, caplog):
        """Default mode logs the text rendering of package exports."""
        _make_py_project(tmp_path)
        cfg = AppConfig(exports_path=tmp_path / "pkg", exports_json=False)
        with caplog.at_level("INFO"):
            exports_run(cfg)
        assert caplog.records

    def test_json_mode_logs_result(self, tmp_path, caplog):
        """JSON mode logs the JSON rendering of package exports."""
        _make_py_project(tmp_path)
        cfg = AppConfig(exports_path=tmp_path / "pkg", exports_json=True)
        with caplog.at_level("INFO"):
            exports_run(cfg)
        assert any("{" in r.message for r in caplog.records)

    def test_write_mode_writes_init_file(self, tmp_path, caplog):
        """`--write` writes the rendering to __init__.py and logs the path."""
        _make_py_project(tmp_path)
        cfg = AppConfig(exports_path=tmp_path / "pkg", exports_write=True)
        with caplog.at_level("INFO"):
            exports_run(cfg)
        init_path = tmp_path / "pkg" / "__init__.py"
        assert init_path.exists()
        assert init_path.read_text().strip() != ""

    # frob:ticket T-0876
    def test_consumers_mode_logs_result(self, tmp_path, caplog):
        """`--consumers SYMBOL` logs the text rendering of who imports it."""
        (tmp_path / "producer.py").write_text("def widget(): ...\n")
        (tmp_path / "consumer.py").write_text("from producer import widget\n")
        cfg = AppConfig(exports_path=tmp_path, exports_consumers="widget")
        with caplog.at_level("INFO"):
            exports_run(cfg)
        assert any("consumer.py" in r.message for r in caplog.records)

    # frob:ticket T-0876
    def test_consumers_mode_json_output(self, tmp_path, caplog):
        """`--consumers SYMBOL --json` logs the JSON ConsumersResult."""
        (tmp_path / "producer.py").write_text("def widget(): ...\n")
        (tmp_path / "consumer.py").write_text("from producer import widget\n")
        cfg = AppConfig(
            exports_path=tmp_path, exports_consumers="widget", exports_json=True
        )
        with caplog.at_level("INFO"):
            exports_run(cfg)
        assert any('"symbol"' in r.message for r in caplog.records)

    # frob:ticket T-0876
    def test_consumers_mode_err_result_exits_1(self, tmp_path, caplog):
        """`--consumers` over a directory with no source files exits 1."""
        empty = tmp_path / "empty"
        empty.mkdir()
        cfg = AppConfig(exports_path=empty, exports_consumers="widget")
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            exports_run(cfg)
        assert exc.value.code == 1


class TestArchRunner:
    """`frob arch`: missing-path error, kwargs overrides, text/JSON output."""

    def test_missing_path_exits_1(self, caplog):
        """No arch_path -- errors and exits 1."""
        cfg = AppConfig(arch_path=None)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            arch_run(cfg)
        assert exc.value.code == 1

    def test_text_mode_with_overrides(self, tmp_path, caplog):
        """Non-default max_function_lines/max_class_methods are forwarded."""
        _make_py_project(tmp_path)
        cfg = AppConfig(
            arch_path=tmp_path,
            arch_max_function_lines=5,
            arch_max_class_methods=1,
            arch_json=False,
        )
        with caplog.at_level("INFO"):
            arch_run(cfg)
        assert caplog.records

    def test_json_mode(self, tmp_path, caplog):
        """JSON mode logs the JSON rendering of the analysis."""
        _make_py_project(tmp_path)
        cfg = AppConfig(arch_path=tmp_path, arch_json=True)
        with caplog.at_level("INFO"):
            arch_run(cfg)
        assert any("{" in r.message for r in caplog.records)


class TestOutlineRunner:
    """`frob outline`: missing-file error, directory fallback to map, file outline."""

    def test_missing_file_exits_1(self, caplog):
        """No outline_file -- errors and exits 1."""
        cfg = AppConfig(outline_file=None)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            outline_run(cfg)
        assert exc.value.code == 1

    def test_directory_target_falls_back_to_map(self, tmp_path, caplog):
        """A directory target delegates to `frob map` with translated flags."""
        _make_py_project(tmp_path)
        cfg = AppConfig(outline_file=tmp_path, outline_json=False, outline_all=True)
        with caplog.at_level("INFO"):
            outline_run(cfg)
        assert caplog.records

    def test_file_target_text_mode(self, tmp_path, caplog):
        """A file target logs the text rendering of its outline."""
        _make_py_project(tmp_path)
        cfg = AppConfig(outline_file=tmp_path / "pkg" / "mod.py", outline_json=False)
        with caplog.at_level("INFO"):
            outline_run(cfg)
        assert caplog.records

    def test_file_target_json_mode(self, tmp_path, caplog):
        """A file target in JSON mode logs the JSON rendering."""
        _make_py_project(tmp_path)
        cfg = AppConfig(outline_file=tmp_path / "pkg" / "mod.py", outline_json=True)
        with caplog.at_level("INFO"):
            outline_run(cfg)
        assert any("{" in r.message for r in caplog.records)

    def test_err_result_exits_1(self, tmp_path, caplog):
        """An unsupported file extension produces an Err and exits 1."""
        bad = tmp_path / "notes.txt"
        bad.write_text("just some text\n")
        cfg = AppConfig(outline_file=bad)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            outline_run(cfg)
        assert exc.value.code == 1


class TestMutateRunner:
    """`frob mutate`: missing-file error, default argv, survivor reporting."""

    def test_missing_file_exits_1(self, caplog):
        """No mutate_file -- errors and exits 1."""
        cfg = AppConfig(mutate_file=None)
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            mutate_run(cfg)
        assert exc.value.code == 1

    def test_err_result_exits_1(self, tmp_path, caplog):
        """A file that run_mutations cannot process errors and exits 1."""
        cfg = AppConfig(
            mutate_file=tmp_path / "does_not_exist.py",
            mutate_path=tmp_path,
            mutate_argv=["true"],
        )
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc:
            mutate_run(cfg)
        assert exc.value.code == 1

    def test_default_argv_used_when_empty(self, tmp_path, monkeypatch):
        """An empty mutate_argv falls back to `uv run pytest -q`."""
        captured = {}

        def fake_run_mutations(root, file, argv):
            captured["argv"] = argv
            from typani import Err

            from frob.mutate import MutateError

            return Err(MutateError.NoSource)

        import frob.mutate as mutate_mod

        monkeypatch.setattr(mutate_mod, "run_mutations", fake_run_mutations)
        cfg = AppConfig(
            mutate_file=tmp_path / "f.py", mutate_path=tmp_path, mutate_argv=[]
        )
        with pytest.raises(SystemExit):
            mutate_run(cfg)
        assert captured["argv"] == ("uv", "run", "pytest", "-q")

    def test_success_no_survivors_text_mode(self, tmp_path, monkeypatch, capsys):
        """A clean mutation run (no survivors) prints a score and does not exit."""
        from typani import Ok

        from frob.mutate import MutationResult

        def fake_run_mutations(root, file, argv):
            return Ok(MutationResult(total=2, killed=2, survivors=()))

        import frob.mutate as mutate_mod

        monkeypatch.setattr(mutate_mod, "run_mutations", fake_run_mutations)
        cfg = AppConfig(
            mutate_file=tmp_path / "f.py", mutate_path=tmp_path, mutate_json=False
        )
        mutate_run(cfg)
        out = capsys.readouterr().out
        assert "mutation score" in out

    def test_success_with_survivors_exits_1(self, tmp_path, monkeypatch, capsys):
        """Surviving mutants are printed and the runner exits 1."""
        from typani import Ok

        from frob.mutate import Mutant, MutationResult

        def fake_run_mutations(root, file, argv):
            return Ok(
                MutationResult(
                    total=2,
                    killed=1,
                    survivors=(Mutant(file="f.py", line=3, description="d"),),
                )
            )

        import frob.mutate as mutate_mod

        monkeypatch.setattr(mutate_mod, "run_mutations", fake_run_mutations)
        cfg = AppConfig(
            mutate_file=tmp_path / "f.py", mutate_path=tmp_path, mutate_json=False
        )
        with pytest.raises(SystemExit) as exc:
            mutate_run(cfg)
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "SURVIVOR" in out

    def test_success_json_mode(self, tmp_path, monkeypatch, capsys):
        """JSON mode prints the report's JSON dump instead of plain text."""
        from typani import Ok

        from frob.mutate import MutationResult

        def fake_run_mutations(root, file, argv):
            return Ok(MutationResult(total=1, killed=1, survivors=()))

        import frob.mutate as mutate_mod

        monkeypatch.setattr(mutate_mod, "run_mutations", fake_run_mutations)
        cfg = AppConfig(
            mutate_file=tmp_path / "f.py", mutate_path=tmp_path, mutate_json=True
        )
        mutate_run(cfg)
        out = capsys.readouterr().out
        assert out.strip().startswith("{")

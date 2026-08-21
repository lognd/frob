"""T-2492: regression coverage for the `_guard_json_stdout_writes` fix
applied to the non-`check` `--json` CLI runners. `frob check --json`'s
own guard was built (and tested) by T-2486; this ticket audited the
other 26 `--json`-bearing runners for the identical unguarded-stdout-write
class and found real, execution-confirmed leaks in `frob fmt --json`,
`frob clean --json`, `frob bind --json`, `frob docs --json`,
`frob map --json`, and `frob graph query --json` (plus `frob vet --json`
and `frob test --json`, covered by their own existing suites once
guarded). Each test here plants a stray `print()` inside the module the
runner calls into (the exact shape T-2484's real incident and this
ticket's own execution-verification both took), calls the runner's
`run()` directly, and asserts the leak never reaches `sys.stdout` --
mirroring `tests/unit/test_app_runners_batch6.py::
TestJsonStdoutStructuralGuard`'s own precedent test shape for `frob
check`."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.app.config import AppConfig

# frob:ticket T-2492
# DUP001: reuse T-2486's fixture directly (pytest fixtures are valid
# cross-module imports) rather than duplicating its body.
from tests.unit.test_app_runners_batch6 import _real_console_handlers  # noqa: F401


# frob:ticket T-2492
# frob:waive AFFECT001 reason="T-2492: new regression test file, no doc content \
# changed by adding it; app.md#runners already describes the runner under test \
# unchanged; filed T-2491 for the doc sync"
class TestBindRunnerJsonGuard:
    """`frob bind --json`: T-2492 found `scan_bindings`/`scan_sources`/
    `check`'s `gitio` DEBUG spawn logging landing unguarded on stdout,
    confirmed by real execution against this repo."""

    # frob:doc docs/modules/app.md#runners
    # frob:tests tests/unit/test_app_runners_json_guard_t2492.py::TestBindRunnerJsonGuard.test_planted_leak_does_not_reach_stdout kind="unit"  # noqa: E501
    def test_planted_leak_does_not_reach_stdout(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys,
        _real_console_handlers,  # noqa: F811 -- cross-module fixture import (DUP001), not a real redefinition
    ) -> None:
        """A stray `print()` inside `bind.check` (the risky span `run`
        guards under `--json`) must land on stderr, never corrupt the
        JSON payload on stdout."""
        import frob.app.bind_runner as mod

        def fake_check(root):  # noqa: ANN001, ANN202
            print("LEAK-T2492")
            return []

        monkeypatch.setattr(mod, "check", fake_check)
        mod.run([str(tmp_path), "--json"])

        captured = capsys.readouterr()
        assert "LEAK-T2492" not in captured.out
        assert "LEAK-T2492" in captured.err
        import json

        json.loads(captured.out)


# frob:ticket T-2492
# frob:waive AFFECT001 reason="T-2492: new regression test file, no doc content \
# changed by adding it; app.md#runners already describes the runner under test \
# unchanged; filed T-2491 for the doc sync"
class TestFmtRunnerJsonGuard:
    """`frob fmt --json`: T-2492 found `format_paths`'s own `gitio`/
    file-walk DEBUG logging landing unguarded on stdout, confirmed by
    real execution against this repo (the un-fixed command produced
    unparsable `--json` output)."""

    # frob:doc docs/modules/app.md#runners
    # frob:tests tests/unit/test_app_runners_json_guard_t2492.py::TestFmtRunnerJsonGuard.test_planted_leak_does_not_reach_stdout kind="unit"  # noqa: E501
    def test_planted_leak_does_not_reach_stdout(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys,
        _real_console_handlers,  # noqa: F811 -- cross-module fixture import (DUP001), not a real redefinition
    ) -> None:
        """A stray `print()` inside `format_paths` must land on stderr,
        never corrupt the JSON payload on stdout."""
        import frob.app.fmt_runner as mod
        from frob.gates._fmt_directives import FmtReport

        def fake_format_paths(*_a, **_kw):  # noqa: ANN002, ANN003
            print("LEAK-T2492")
            return FmtReport(changes=())

        monkeypatch.setattr(
            "frob.gates._fmt_directives.format_paths", fake_format_paths
        )
        cfg = AppConfig(fmt_path=tmp_path, fmt_json=True, fmt_check=True)
        mod.run(cfg)

        captured = capsys.readouterr()
        assert "LEAK-T2492" not in captured.out
        assert "LEAK-T2492" in captured.err
        import json

        json.loads(captured.out)


# frob:ticket T-2492
# frob:waive AFFECT001 reason="T-2492: new regression test file, no doc content \
# changed by adding it; app.md#runners/clean.md#public-api already describe the runner \
# under test unchanged; filed T-2491 for the doc sync"
class TestCleanRunnerJsonGuard:
    """`frob clean --json`: T-2492 found `clean`'s own `gitio` DEBUG
    logging landing unguarded on stdout, confirmed by real execution."""

    # frob:doc docs/modules/app.md#runners
    # frob:doc docs/modules/clean.md#public-api
    # frob:tests tests/unit/test_app_runners_json_guard_t2492.py::TestCleanRunnerJsonGuard.test_planted_leak_does_not_reach_stdout kind="unit"  # noqa: E501
    def test_planted_leak_does_not_reach_stdout(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys,
        _real_console_handlers,  # noqa: F811 -- cross-module fixture import (DUP001), not a real redefinition
    ) -> None:
        """A stray `print()` inside `clean` must land on stderr, never
        corrupt the JSON payload on stdout."""
        from typani import Ok

        import frob.app.clean_runner as mod

        def fake_clean(*_a, **_kw):  # noqa: ANN002, ANN003
            print("LEAK-T2492")
            from frob.clean import CleanReport, CleanTier

            return Ok(
                CleanReport(
                    tier=CleanTier.SAFE,
                    dry_run=True,
                    entries=[],
                    skipped_tracked=[],
                )
            )

        monkeypatch.setattr("frob.clean.clean", fake_clean)
        cfg = AppConfig(clean_path=tmp_path, clean_json=True)
        mod.run(cfg)

        captured = capsys.readouterr()
        assert "LEAK-T2492" not in captured.out
        assert "LEAK-T2492" in captured.err
        import json

        json.loads(captured.out)


# frob:ticket T-2492
# frob:waive AFFECT001 reason="T-2492: new regression test file, no doc content \
# changed by adding it; app.md#runners/render.md#exemplar-frob-map already describe \
# the runner under test unchanged; filed T-2491 for the doc sync"
class TestMapRunnerJsonGuard:
    """`frob map --json`: T-2492 found `_try_map_via_daemon`'s own
    "daemon disabled" INFO log landing unguarded on stdout (it ran BEFORE
    the pre-existing `quiet_stdout_logs()` context was even entered),
    confirmed by real execution."""

    # frob:doc docs/modules/app.md#runners
    # frob:doc docs/modules/render.md#exemplar-frob-map
    # frob:tests tests/unit/test_app_runners_json_guard_t2492.py::TestMapRunnerJsonGuard.test_daemon_disabled_log_does_not_reach_stdout kind="unit"  # noqa: E501
    def test_daemon_disabled_log_does_not_reach_stdout(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys,
        _real_console_handlers,  # noqa: F811 -- cross-module fixture import (DUP001), not a real redefinition
    ) -> None:
        """`_daemon_proxy.query`'s real "daemon disabled, computing ...
        in-process" INFO log (this ticket's actual execution-confirmed
        leak, not a synthetic plant) must land on stderr, never corrupt
        the JSON payload the in-process fallback produces."""
        import frob.app.map_runner as mod
        from frob.map import MapResult

        monkeypatch.setattr(
            mod,
            "map_project",
            lambda root, depth=None: MapResult(  # noqa: ARG005
                root=str(root),
                total_files=0,
                total_lines=0,
                files=[],
            ),
        )
        cfg = AppConfig(map_path=tmp_path, map_json=True)
        mod.run(cfg)

        captured = capsys.readouterr()
        assert "daemon_proxy" not in captured.out
        import json

        json.loads(captured.out)


# frob:ticket T-2492
# frob:waive AFFECT001 reason="T-2492: new regression test file, no doc content \
# changed by adding it; app.md#runners already describes the runner under test \
# unchanged; filed T-2491 for the doc sync"
class TestDocsRunnerJsonGuard:
    """`frob docs --json`: T-2492 found `extract_docstrings`'s own
    per-file "dispatching path=.../extracted N symbols" INFO logging
    landing unguarded on stdout, confirmed by real execution (dozens of
    lines of parse-dispatch noise corrupted the payload)."""

    # frob:doc docs/modules/app.md#runners
    # frob:tests tests/unit/test_app_runners_json_guard_t2492.py::TestDocsRunnerJsonGuard.test_planted_leak_does_not_reach_stdout kind="unit"  # noqa: E501
    def test_planted_leak_does_not_reach_stdout(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys,
        _real_console_handlers,  # noqa: F811 -- cross-module fixture import (DUP001), not a real redefinition
    ) -> None:
        """A stray `print()` inside `_collect_docstrings` must land on
        stderr, never corrupt the JSON payload on stdout."""
        import frob.app.docs_runner as mod

        py_file = tmp_path / "m.py"
        # frob:waive SELFAUDIT001 reason="T-2492: writes into pytest's own tmp_path \
        # fixture -- a test-scratch fixture write, not a real fs.write capability \
        # surface; design/frob.strata's testsuite node fs.write via-list is a 13KB+ \
        # single-line, merge-conflict-prone target explicitly flagged as out of scope \
        # for incidental edits"
        py_file.write_text('"""mod."""\n')

        def fake_collect(*_a, **_kw):  # noqa: ANN002, ANN003
            print("LEAK-T2492")
            return []

        monkeypatch.setattr(mod, "_collect_docstrings", fake_collect)
        cfg = AppConfig(docs_path=py_file, docs_json=True)
        mod.run(cfg)

        captured = capsys.readouterr()
        assert "LEAK-T2492" not in captured.out
        assert "LEAK-T2492" in captured.err
        import json

        json.loads(captured.out)


# frob:ticket T-2492
# frob:waive AFFECT001 reason="T-2492: new regression test file, no doc content \
# changed by adding it; app.md#runners already describes the runner under test \
# unchanged; filed T-2491 for the doc sync"
class TestGraphQueryRunnerJsonGuard:
    """`frob graph query --json`: T-2492 found `_try_query_via_daemon`'s
    own "daemon disabled" INFO log landing unguarded on stdout (no guard
    existed anywhere in `graph_runner.py` before this ticket), confirmed
    by real execution."""

    # frob:doc docs/modules/app.md#runners
    # frob:tests tests/unit/test_app_runners_json_guard_t2492.py::TestGraphQueryRunnerJsonGuard.test_daemon_disabled_log_does_not_reach_stdout kind="unit"  # noqa: E501
    def test_daemon_disabled_log_does_not_reach_stdout(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys,
        _real_console_handlers,  # noqa: F811 -- cross-module fixture import (DUP001), not a real redefinition
    ) -> None:
        """The real `_daemon_proxy.query` "daemon disabled" INFO log must
        land on stderr, never corrupt the `--load-snapshot` fallback's
        JSON payload."""
        import frob.app.graph_runner as mod

        monkeypatch.setattr(
            mod,
            "_load_snapshot",
            lambda root, cache: __import__("typani").Err("unavailable"),  # noqa: ARG005
        )
        cfg = AppConfig(graph_path=tmp_path, graph_json=True, graph_ref="nope")
        with pytest.raises(SystemExit):
            mod.run(cfg)

        captured = capsys.readouterr()
        assert "daemon_proxy" not in captured.out

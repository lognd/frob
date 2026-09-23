"""Unit tests for `frob.testing._unity_batchmode` (T-4508): the NUnit3
batchmode-XML parser against a static fixture, editor resolution
precedence (`[tool.frob] unity_editor` pyproject override vs T-4501's
doctor lookup), and `run_unity_batchmode` end-to-end against a fake Unity
executable placed on `PATH` (never a real Unity binary)."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from frob.testing._unity_batchmode import (
    UnityBatchmodeError,
    parse_unity_batchmode_xml,
    resolve_unity_editor,
    run_unity_batchmode,
)

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "lang" / "csharp" / "tests"

_NODE_A = (
    "tests/SampleUnityTests.cs::Frob.Fixtures.Csharp.SampleUnityTests"
    "::SpawnsPlayerNextFrame"
)
_NODE_B = (
    "tests/SampleUnityTests.cs::Frob.Fixtures.Csharp.SampleUnityTests::MovesPlayerRight"
)


class TestParseUnityBatchmodeXml:
    """`parse_unity_batchmode_xml` against the static NUnit3 fixture
    `tests/fixtures/lang/csharp/tests/sample_unity_results.xml`."""

    # frob:tests tests/unit/test_unity_batchmode.py::TestParseUnityBatchmodeXml.test_parses_nested_test_suites_into_fqn_result_map  # noqa: E501
    def test_parses_nested_test_suites_into_fqn_result_map(self) -> None:
        # frob:tests src/frob/testing/_unity_batchmode.py::parse_unity_batchmode_xml
        text = (_FIXTURES_DIR / "sample_unity_results.xml").read_text(encoding="utf-8")
        result = parse_unity_batchmode_xml(text)
        assert result.is_ok
        assert result.danger_ok == {
            "Frob.Fixtures.Csharp.SampleUnityTests.SpawnsPlayerNextFrame": "Passed",
            "Frob.Fixtures.Csharp.SampleUnityTests.MovesPlayerRight": "Failed",
        }

    # frob:tests tests/unit/test_unity_batchmode.py::TestParseUnityBatchmodeXml.test_malformed_xml_is_err_not_empty  # noqa: E501
    # frob:tests src/frob/testing/_unity_batchmode.py::UnityBatchmodeError
    def test_malformed_xml_is_err_not_empty(self) -> None:
        # frob:tests src/frob/testing/_unity_batchmode.py::parse_unity_batchmode_xml
        text = (_FIXTURES_DIR / "malformed_results.xml").read_text(encoding="utf-8")
        result = parse_unity_batchmode_xml(text)
        assert result.is_err
        assert result.danger_err == UnityBatchmodeError.ResultsUnreadable


class TestResolveUnityEditor:
    """`resolve_unity_editor`'s precedence: `[tool.frob] unity_editor`
    pyproject override before T-4501's doctor lookup (T-4508)."""

    # frob:tests tests/unit/test_unity_batchmode.py::TestResolveUnityEditor.test_pyproject_override_wins  # noqa: E501
    def test_pyproject_override_wins(self, tmp_path: Path) -> None:
        # frob:tests src/frob/testing/_unity_batchmode.py::resolve_unity_editor
        (tmp_path / "pyproject.toml").write_text(
            '[tool.frob]\nunity_editor = "/opt/unity/Unity"\n', encoding="utf-8"
        )
        assert resolve_unity_editor(tmp_path) == "/opt/unity/Unity"

    # frob:tests tests/unit/test_unity_batchmode.py::TestResolveUnityEditor.test_no_override_falls_back_to_doctor_lookup  # noqa: E501
    def test_no_override_falls_back_to_doctor_lookup(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/testing/_unity_batchmode.py::resolve_unity_editor
        monkeypatch.delenv("UNITY_PATH", raising=False)
        monkeypatch.delenv("UNITY_EDITOR", raising=False)
        fake_editor = tmp_path / "Unity"
        fake_editor.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        fake_editor.chmod(0o755)
        monkeypatch.setenv("UNITY_PATH", str(fake_editor))
        assert resolve_unity_editor(tmp_path) == str(fake_editor)

    # frob:tests tests/unit/test_unity_batchmode.py::TestResolveUnityEditor.test_nothing_resolves_is_none  # noqa: E501
    def test_nothing_resolves_is_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/testing/_unity_batchmode.py::resolve_unity_editor
        monkeypatch.delenv("UNITY_PATH", raising=False)
        monkeypatch.delenv("UNITY_EDITOR", raising=False)
        monkeypatch.setattr("shutil.which", lambda _name: None)
        assert resolve_unity_editor(tmp_path) is None


# frob:waive WIRE001 reason="a fixture helper used only by this file's own tests to \
# fake a Unity Editor binary on PATH -- there is no production caller to wire it to by \
# design" permanent="true"
def _write_fake_unity(bin_dir: Path, fixture_name: str, exit_code: int = 0) -> Path:
    """A fake Unity Editor executable that copies the named static NUnit3
    fixture to whatever `-testResults <path>` names, then exits
    `exit_code` -- never a real Unity binary (T-4508's own instruction)."""
    fixture_path = _FIXTURES_DIR / fixture_name
    script = bin_dir / "Unity"
    script.write_text(
        "#!/bin/sh\n"
        'out=""\n'
        "while [ $# -gt 0 ]; do\n"
        '  if [ "$1" = "-testResults" ]; then out="$2"; fi\n'
        "  shift\n"
        "done\n"
        f'if [ -n "$out" ]; then cp "{fixture_path}" "$out"; fi\n'
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return script


# frob:waive WIRE001 reason="a fixture helper used only by this file's own tests to \
# fake a crashing Unity Editor binary on PATH -- there is no production caller to wire \
# it to by design" permanent="true"
def _write_crashing_unity(bin_dir: Path) -> Path:
    """A fake Unity Editor that crashes without ever writing a results
    file -- T-4508's third acceptance criterion."""
    script = bin_dir / "Unity"
    script.write_text(
        "#!/bin/sh\necho 'license failure' >&2\nexit 1\n", encoding="utf-8"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return script


class TestRunUnityBatchmode:
    """`run_unity_batchmode` end-to-end (T-4508), driven entirely by a
    fake Unity executable -- no real Unity process is ever spawned."""

    # frob:tests tests/unit/test_unity_batchmode.py::TestRunUnityBatchmode.test_maps_passing_and_failing_ids  # noqa: E501
    def test_maps_passing_and_failing_ids(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/testing/_unity_batchmode.py::run_unity_batchmode
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        editor = _write_fake_unity(bin_dir, "sample_unity_results.xml")
        monkeypatch.setenv("UNITY_PATH", str(editor))

        result = run_unity_batchmode((_NODE_A, _NODE_B), tmp_path)
        assert result.is_ok
        assert result.danger_ok == {_NODE_A: True, _NODE_B: False}

    # frob:tests tests/unit/test_unity_batchmode.py::TestRunUnityBatchmode.test_editor_not_found_is_err  # noqa: E501
    # frob:tests src/frob/testing/_unity_batchmode.py::UnityBatchmodeError
    def test_editor_not_found_is_err(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/testing/_unity_batchmode.py::run_unity_batchmode
        monkeypatch.delenv("UNITY_PATH", raising=False)
        monkeypatch.delenv("UNITY_EDITOR", raising=False)
        monkeypatch.setattr("shutil.which", lambda _name: None)

        result = run_unity_batchmode((_NODE_A,), tmp_path)
        assert result.is_err
        assert result.danger_err == UnityBatchmodeError.EditorNotFound

    # frob:tests tests/unit/test_unity_batchmode.py::TestRunUnityBatchmode.test_crash_with_no_results_file_is_run_failed_distinct_from_a_test_failure  # noqa: E501
    def test_crash_with_no_results_file_is_run_failed_distinct_from_a_test_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # T-4508's third acceptance criterion: an editor crash/license
        # failure must surface as a distinct error, never an empty
        # {node_id: False}-shaped silent pass on zero collected results.
        # frob:tests src/frob/testing/_unity_batchmode.py::run_unity_batchmode
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        editor = _write_crashing_unity(bin_dir)
        monkeypatch.setenv("UNITY_PATH", str(editor))

        result = run_unity_batchmode((_NODE_A,), tmp_path)
        assert result.is_err
        assert result.danger_err == UnityBatchmodeError.RunFailed

    # frob:tests tests/unit/test_unity_batchmode.py::TestRunUnityBatchmode.test_requested_id_missing_from_results_is_err  # noqa: E501
    def test_requested_id_missing_from_results_is_err(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/testing/_unity_batchmode.py::run_unity_batchmode
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        editor = _write_fake_unity(bin_dir, "sample_unity_results.xml")
        monkeypatch.setenv("UNITY_PATH", str(editor))

        unknown_node = (
            "tests/SampleUnityTests.cs::Frob.Fixtures.Csharp.SampleUnityTests"
            "::NoSuchMethod"
        )
        result = run_unity_batchmode((unknown_node,), tmp_path)
        assert result.is_err
        assert result.danger_err == UnityBatchmodeError.ResultsUnreadable

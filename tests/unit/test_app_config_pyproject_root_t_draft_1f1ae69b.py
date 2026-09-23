"""Direct-call coverage for `frob.app.config._pyproject_file_for_args`
(T-4502).

`AppConfig.from_args` used to read `[tool.frob]` config from an
unconditional `Path("pyproject.toml")` (process-cwd-relative), never the
root a `frob ticket <verb> --path <ROOT>` invocation itself names. That
silently leaked THIS repo's own `[tool.frob]` table (e.g. T-4496's
`ticket_land_branch = "dev"`) into every `frob ticket land --path
<unrelated-tmp-root>` call made with this repo as CWD -- every system
test, and every real dev/CI invocation -- which is exactly the failure
`tests/system/test_cli_ticket_land.py::TestLandCLI::
test_dry_run_reports_clean` reproduces at the CLI/subprocess layer. These
tests cover the smaller, directly-callable unit underneath that fix:
`_pyproject_file_for_args`'s explicit-path/FROB_ROOT/cwd precedence.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from frob.app.config import _pyproject_file_for_args


class TestPyprojectFileForArgs:
    # frob:tests src/frob/app/config.py::_pyproject_file_for_args kind="unit"
    # frob:tests src/frob/app/config.py::AppConfig.from_args kind="unit"
    def test_explicit_ticket_path_wins_over_cwd(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py::TestPyprojectFileForArgs.test_explicit_ticket_path_wins_over_cwd  # noqa: E501
        root = tmp_path / "root"
        root.mkdir()
        args = argparse.Namespace(ticket_path=str(root))
        assert _pyproject_file_for_args(args) == root / "pyproject.toml"

    # frob:tests src/frob/app/config.py::_pyproject_file_for_args kind="unit"

    # frob:tests src/frob/app/config.py::AppConfig.from_args kind="unit"
    def test_frob_root_env_wins_over_cwd_when_no_explicit_path(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py::TestPyprojectFileForArgs.test_frob_root_env_wins_over_cwd_when_no_explicit_path  # noqa: E501
        env_root = tmp_path / "env_root"
        env_root.mkdir()
        monkeypatch.setenv("FROB_ROOT", str(env_root))
        args = argparse.Namespace(ticket_path=".")
        assert _pyproject_file_for_args(args) == env_root / "pyproject.toml"

    # frob:tests src/frob/app/config.py::AppConfig.from_args kind="unit"
    # frob:tests src/frob/app/config.py::_pyproject_file_for_args kind="unit"
    def test_bare_dot_ticket_path_falls_back_to_cwd(self, monkeypatch) -> None:
        # frob:tests \
        # tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py::TestPyprojectFileForArgs.test_bare_dot_ticket_path_falls_back_to_cwd  # noqa: E501
        monkeypatch.delenv("FROB_ROOT", raising=False)
        args = argparse.Namespace(ticket_path=".")
        assert _pyproject_file_for_args(args) == Path("pyproject.toml")

    # frob:tests src/frob/app/config.py::AppConfig.from_args kind="unit"
    # frob:tests src/frob/app/config.py::_pyproject_file_for_args kind="unit"
    def test_non_ticket_subcommand_is_unaffected(self, monkeypatch) -> None:
        # frob:tests \
        # tests/unit/test_app_config_pyproject_root_t_draft_1f1ae69b.py::TestPyprojectFileForArgs.test_non_ticket_subcommand_is_unaffected  # noqa: E501
        monkeypatch.delenv("FROB_ROOT", raising=False)
        args = argparse.Namespace(subcommand="check")
        assert _pyproject_file_for_args(args) == Path("pyproject.toml")

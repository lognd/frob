"""Direct-call coverage for `frob.app.config.AppConfig.from_external`/
`.from_args` (T-1276).

Both are only exercised today via subprocess CLI tests (every real `frob`
invocation calls one or the other to build its own `AppConfig`), which
pytest-cov cannot attribute back to the running process -- hence their
0.0%-branch TEST005 findings despite being behaviorally exercised on
every single CLI dispatch. These tests build a bare `argparse.Namespace`
and call
`from_external`/`from_args` directly, covering: no config file present,
a `pyproject.toml` `[tool.frob]` table present and merged, `subcommand`
resolution to the `Subcommand` enum, the `no_color` special-case field,
a representative string field and a representative bool flag from the
two big copy-loops, and `from_args`'s own default-path delegation to
`from_external`.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from frob.app.config import AppConfig, Subcommand


class TestFromExternal:
    def test_missing_file_falls_back_to_defaults(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_miss\
        # ing_file_falls_back_to_defaults
        args = argparse.Namespace()
        cfg = AppConfig.from_external(args, tmp_path / "nonexistent.toml")
        assert cfg.subcommand is None
        assert cfg.no_color is False

    def test_reads_and_merges_tool_frob_table(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_read\
        # s_and_merges_tool_frob_table
        cfg_file = tmp_path / "pyproject.toml"
        cfg_file.write_text('[tool.frob]\ncheck_type = "lint"\n')
        args = argparse.Namespace()
        cfg = AppConfig.from_external(args, cfg_file)
        assert cfg.check_type == "lint"

    def test_subcommand_is_resolved_to_the_enum(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_subc\
        # ommand_is_resolved_to_the_enum
        args = argparse.Namespace(subcommand="doctor")
        cfg = AppConfig.from_external(args, tmp_path / "nonexistent.toml")
        assert cfg.subcommand is Subcommand.doctor

    def test_no_color_flag_is_copied_when_present(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_no_c\
        # olor_flag_is_copied_when_present
        args = argparse.Namespace(no_color=True)
        cfg = AppConfig.from_external(args, tmp_path / "nonexistent.toml")
        assert cfg.no_color is True

    def test_string_field_from_the_first_copy_loop_is_carried(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_stri\
        # ng_field_from_the_first_copy_loop_is_carried
        args = argparse.Namespace(check_type="policy", check_ticket="T-0001")
        cfg = AppConfig.from_external(args, tmp_path / "nonexistent.toml")
        assert cfg.check_type == "policy"
        assert cfg.check_ticket == "T-0001"

    def test_bool_flag_from_the_second_copy_loop_defaults_false(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_bool\
        # _flag_from_the_second_copy_loop_defaults_false
        args = argparse.Namespace()
        cfg = AppConfig.from_external(args, tmp_path / "nonexistent.toml")
        assert cfg.fmt_check is False

    def test_bool_flag_from_the_second_copy_loop_is_set_true(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_bool\
        # _flag_from_the_second_copy_loop_is_set_true
        args = argparse.Namespace(fmt_check=True)
        cfg = AppConfig.from_external(args, tmp_path / "nonexistent.toml")
        assert cfg.fmt_check is True


class TestFromArgs:
    def test_delegates_to_from_external_with_pyproject_default(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromArgs.test_delegate\
        # s_to_from_external_with_pyproject_default
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[tool.frob]\ncheck_type = "lint"\n')
        args = argparse.Namespace(subcommand="check")
        cfg = AppConfig.from_args(args)
        assert cfg.subcommand is Subcommand.check
        assert cfg.check_type == "lint"

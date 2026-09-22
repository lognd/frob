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
    # frob:tests src/frob/app/config.py::AppConfig.from_external kind="unit"  # noqa: E501
    def test_missing_file_falls_back_to_defaults(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_missing_file_falls_back_to_defaults  # noqa: E501
        args = argparse.Namespace()
        cfg = AppConfig.from_external(args, tmp_path / "nonexistent.toml")
        assert cfg.subcommand is None
        assert cfg.no_color is False

    def test_reads_and_merges_tool_frob_table(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_reads_and_merges_tool_frob_table  # noqa: E501
        cfg_file = tmp_path / "pyproject.toml"
        cfg_file.write_text('[tool.frob]\ncheck_type = "lint"\n')
        args = argparse.Namespace()
        cfg = AppConfig.from_external(args, cfg_file)
        assert cfg.check_type == "lint"

    def test_subcommand_is_resolved_to_the_enum(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_subcommand_is_resolved_to_the_enum  # noqa: E501
        args = argparse.Namespace(subcommand="doctor")
        cfg = AppConfig.from_external(args, tmp_path / "nonexistent.toml")
        assert cfg.subcommand is Subcommand.doctor

    def test_no_color_flag_is_copied_when_present(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_no_color_flag_is_copied_when_present  # noqa: E501
        args = argparse.Namespace(no_color=True)
        cfg = AppConfig.from_external(args, tmp_path / "nonexistent.toml")
        assert cfg.no_color is True

    def test_string_field_from_the_first_copy_loop_is_carried(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_string_field_from_the_first_copy_loop_is_carried  # noqa: E501
        args = argparse.Namespace(check_type="policy", check_ticket="T-0001")
        cfg = AppConfig.from_external(args, tmp_path / "nonexistent.toml")
        assert cfg.check_type == "policy"
        assert cfg.check_ticket == "T-0001"

    def test_bool_flag_from_the_second_copy_loop_defaults_false(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_bool_flag_from_the_second_copy_loop_defaults_false  # noqa: E501
        args = argparse.Namespace()
        cfg = AppConfig.from_external(args, tmp_path / "nonexistent.toml")
        assert cfg.fmt_check is False

    def test_bool_flag_from_the_second_copy_loop_is_set_true(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_bool_flag_from_the_second_copy_loop_is_set_true  # noqa: E501
        args = argparse.Namespace(fmt_check=True)
        cfg = AppConfig.from_external(args, tmp_path / "nonexistent.toml")
        assert cfg.fmt_check is True

    def test_unsized_ack_reason_reaches_cfg(self, tmp_path: Path) -> None:
        """T-4702 (T-5132 regression fix): `--unsized-ack REASON` was
        silently dropped -- `ticket_unsized_ack` was missing from
        `_STRING_FIELDS`, so `cfg.ticket_unsized_ack` was always `None`
        regardless of what the CLI flag carried."""
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_unsized_ack_reason_reaches_cfg  # noqa: E501
        args = argparse.Namespace(ticket_unsized_ack="filed as T-9999, sized later")
        cfg = AppConfig.from_external(args, tmp_path / "nonexistent.toml")
        assert cfg.ticket_unsized_ack == "filed as T-9999, sized later"

    def test_ticket_points_int_field_reaches_cfg(self, tmp_path: Path) -> None:
        """T-4702 (T-5132 regression fix): `ticket_points` was missing
        from `_INT_FIELDS` alongside `ticket_unsized_ack`, so `frob ticket
        points` values were dropped the same way before this fix."""
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromExternal.test_ticket_points_int_field_reaches_cfg  # noqa: E501
        args = argparse.Namespace(ticket_points=3)
        cfg = AppConfig.from_external(args, tmp_path / "nonexistent.toml")
        assert cfg.ticket_points == 3


class TestFromArgs:
    def test_delegates_to_from_external_with_pyproject_default(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests \
        # tests/unit/test_app_config_from_external_t1276.py::TestFromArgs.test_delegates_to_from_external_with_pyproject_default  # noqa: E501
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[tool.frob]\ncheck_type = "lint"\n')
        args = argparse.Namespace(subcommand="check")
        cfg = AppConfig.from_args(args)
        assert cfg.subcommand is Subcommand.check
        assert cfg.check_type == "lint"

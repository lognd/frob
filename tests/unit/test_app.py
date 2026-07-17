import argparse
from pathlib import Path

from frob.app.config import AppConfig, Subcommand


def _args(**kwargs) -> argparse.Namespace:
    defaults = {
        "subcommand": None,
        "scaffold_command": None,
        "scaffold_type": None,
        "scaffold_name": None,
        "scaffold_output": None,
        "scaffold_force": False,
        "cycle_path": None,
        "cycle_lang": None,
        "cycle_suggest": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_config_no_subcommand():
    cfg = AppConfig.from_args(_args())
    assert cfg.subcommand is None


def test_config_scaffold_new_subcommand():
    cfg = AppConfig.from_args(
        _args(
            subcommand="scaffold",
            scaffold_command="new",
            scaffold_type="python-tool",
            scaffold_name="mypkg",
        )
    )
    assert cfg.subcommand == Subcommand.scaffold
    assert cfg.scaffold_type == "python-tool"
    assert cfg.scaffold_name == "mypkg"


def test_config_cycle_subcommand():
    cfg = AppConfig.from_args(_args(subcommand="cycle", cycle_path="src/"))
    assert cfg.subcommand == Subcommand.cycle
    assert cfg.cycle_path == Path("src/")


def test_config_reads_toml_file(tmp_path):
    cfg_file = tmp_path / "pyproject.toml"
    cfg_file.write_text("[tool.frob]\ncycle_suggest = true\n")
    cfg = AppConfig.from_external(
        _args(subcommand="cycle", cycle_path="src/"), cfg_file
    )
    assert cfg.cycle_suggest is True


def test_config_cli_overrides_file(tmp_path):
    cfg_file = tmp_path / "pyproject.toml"
    cfg_file.write_text("[tool.frob]\ncycle_suggest = false\n")
    cfg = AppConfig.from_external(
        _args(subcommand="cycle", cycle_path="src/", cycle_suggest=True), cfg_file
    )
    assert cfg.cycle_suggest is True

import argparse
from pathlib import Path

from frob.app.config import AppConfig, Subcommand


def _args(**kwargs) -> argparse.Namespace:
    defaults = {
        "subcommand": None,
        "init_command": None,
        "init_type": None,
        "init_name": None,
        "init_output": None,
        "init_force": False,
        "cycle_path": None,
        "cycle_lang": None,
        "cycle_suggest": False,
        "stub_file": None,
        "stub_target": None,
        "stub_output": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_config_no_subcommand():
    cfg = AppConfig.from_args(_args())
    assert cfg.subcommand is None


def test_config_stub_subcommand():
    cfg = AppConfig.from_args(
        _args(subcommand="stub", stub_file="src/foo.py", stub_target="bar")
    )
    assert cfg.subcommand == Subcommand.stub
    assert cfg.stub_file == Path("src/foo.py")
    assert cfg.stub_target == "bar"


def test_config_init_new_subcommand():
    cfg = AppConfig.from_args(
        _args(
            subcommand="init",
            init_command="new",
            init_type="python-tool",
            init_name="mypkg",
        )
    )
    assert cfg.subcommand == Subcommand.init
    assert cfg.init_type == "python-tool"
    assert cfg.init_name == "mypkg"


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

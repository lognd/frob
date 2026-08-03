"""Unit tests for `frob.strata._scope_config` -- the `[strata]` table of
`frob.toml` (T-1451, docs/strata/surface.md#may-scope)."""

from __future__ import annotations

from pathlib import Path

from frob.strata._scope_config import StrataScopeConfig, load_strata_scope_config


class TestStrataScopeConfig:
    # frob:tests src/frob/strata/_scope_config.py::load_strata_scope_config kind="unit"
    def test_missing_frob_toml_returns_defaults(self, tmp_path: Path):
        """No `frob.toml` at all -- fail-open, `require_may_scope=False`."""
        config = load_strata_scope_config(tmp_path)
        assert config == StrataScopeConfig()
        assert config.require_may_scope is False
        assert config.require_may_scope_threshold is None

    # frob:tests src/frob/strata/_scope_config.py::load_strata_scope_config kind="unit"
    def test_parses_strata_table(self, tmp_path: Path):
        (tmp_path / "frob.toml").write_text(
            "[strata]\nrequire_may_scope = true\nrequire_may_scope_threshold = 5\n",
            encoding="utf-8",
        )
        config = load_strata_scope_config(tmp_path)
        assert config.require_may_scope is True
        assert config.require_may_scope_threshold == 5

    # frob:tests src/frob/strata/_scope_config.py::load_strata_scope_config kind="unit"
    def test_malformed_toml_falls_back_to_defaults(self, tmp_path: Path):
        (tmp_path / "frob.toml").write_text("not [ valid toml", encoding="utf-8")
        config = load_strata_scope_config(tmp_path)
        assert config == StrataScopeConfig()

    # frob:tests src/frob/strata/_scope_config.py::load_strata_scope_config kind="unit"
    def test_wrong_typed_strata_table_falls_back_to_defaults(self, tmp_path: Path):
        (tmp_path / "frob.toml").write_text("strata = 5\n", encoding="utf-8")
        config = load_strata_scope_config(tmp_path)
        assert config == StrataScopeConfig()

    # frob:tests src/frob/strata/_scope_config.py::load_strata_scope_config kind="unit"
    def test_no_strata_table_present_returns_defaults(self, tmp_path: Path):
        (tmp_path / "frob.toml").write_text("[graph]\nexclude = []\n", encoding="utf-8")
        config = load_strata_scope_config(tmp_path)
        assert config == StrataScopeConfig()

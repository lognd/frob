"""frob.strata._scope_config -- the `[strata]` table of `frob.toml` (T-1451).

One reader, one shape: `require_may_scope` escalates SYS107 (T-1451's
via-less-may-on-a-large-node advisory, `_selfconform.py`) from its default
WARN severity to ERROR, for a repo whose owner is ready to commit to full
`may ... via ...` scoping and wants CI to actually enforce it rather than
merely advise it. Follows the SAME fail-open, best-effort-TOML shape every
other `frob.toml` table reader in this repo uses (`frob.tomlio.
read_toml_lenient`, T-0861) -- a missing/malformed `[strata]` table is
never a crash, just defaults.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger
from frob.tomlio import read_toml_lenient

_log = get_logger(__name__)


# frob:doc docs/strata/surface.md#may-scope
# frob:ticket T-1451
class StrataScopeConfig(BaseModel):
    """The `[strata]` table of `frob.toml`: `require_may_scope` escalates
    SYS107 (a via-less `may` grant on a large node, `_selfconform.py`) from
    WARN to ERROR. `require_may_scope_threshold`, when set, overrides
    SYS107's own default file-count threshold
    (`_selfconform.py::_LARGE_NODE_FILE_THRESHOLD`) for THIS repo -- `None`
    (the default) means "use the built-in threshold"."""

    model_config = ConfigDict(frozen=True)

    require_may_scope: bool = False
    require_may_scope_threshold: int | None = None


def _read_toml(path: Path) -> dict | None:
    """Best-effort TOML load for `[strata]`, split out purely to name this
    module's own `log_prefix` -- see `StrataScopeConfig`'s docstring for
    the fail-open contract."""
    return read_toml_lenient(path, log_prefix="strata-scope")


# frob:doc docs/strata/surface.md#may-scope
# frob:ticket T-1451
# frob:tests tests/unit/strata/test_scope_config.py::TestStrataScopeConfig.test_missing_frob_toml_returns_defaults  # noqa: E501
# frob:tests tests/unit/strata/test_scope_config.py::TestStrataScopeConfig.test_parses_strata_table  # noqa: E501
# frob:tests tests/unit/strata/test_scope_config.py::TestStrataScopeConfig.test_malformed_toml_falls_back_to_defaults  # noqa: E501
# frob:tests tests/unit/strata/test_scope_config.py::TestStrataScopeConfig.test_wrong_typed_strata_table_falls_back_to_defaults  # noqa: E501
def load_strata_scope_config(root: Path) -> StrataScopeConfig:
    """The `[strata]` table from `root/frob.toml`, or all-defaults
    (`require_may_scope=False`) on a missing/malformed file/table -- never
    raises, mirrors `frob.perf._sketch_store.load_sketch_config`'s exact
    shape (T-0861 precedent)."""
    data = _read_toml(root / "frob.toml")
    if data is None:
        return StrataScopeConfig()
    table = data.get("strata", {})
    if not isinstance(table, dict):
        _log.warning("strata-scope: [strata] is not a table, using defaults")
        return StrataScopeConfig()
    try:
        return StrataScopeConfig(**table)
    except (TypeError, ValueError) as exc:
        _log.warning("strata-scope: [strata] rejected (%s), using defaults", exc)
        return StrataScopeConfig()

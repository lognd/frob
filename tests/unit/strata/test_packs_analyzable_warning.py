"""SF-11 regression: `require_analyzable`'s auto-inject WARNing must fire at
most once per module identity per process, not once per `load_design_ids`
call site (docs/strata/policy.md#packs).

Positive control: at HEAD c8f56ef10 (before this fix) calling
`load_design_ids` twice in one process emits TWO such WARNING records for
frob's own design/ tree, because it has trusted nodes and never declares
`std.policy.analyzable` -- 570 occurrences across 45 land logs, ~12.7 per
land (STRATA-FRICTION.md SF-11).
"""

from __future__ import annotations

import logging
from pathlib import Path

from frob.strata import _packs as _packs_module
from frob.strata._design_load import load_design_ids
from frob.strata._packs import require_analyzable

_WARNING_SNIPPET = "auto-injecting mandatory base pack"


def _repo_root() -> Path:
    """The frob checkout root, three parents up from this test file."""
    return Path(__file__).resolve().parents[3]


class TestAnalyzableWarningDeduped:
    # frob:tests tests/unit/strata/test_packs_analyzable_warning.py::TestAnalyzableWarningDeduped.test_load_design_ids_twice_warns_once  # noqa: E501
    def test_load_design_ids_twice_warns_once(self, caplog, monkeypatch):
        """Two `load_design_ids` calls over the same design/ tree in one
        process must produce at most one auto-inject WARNING (SF-11)."""
        monkeypatch.setattr(
            "frob.strata._packs._WARNED_ANALYZABLE_MODULES", set(), raising=True
        )
        root = _repo_root()
        with caplog.at_level(logging.WARNING, logger="frob.strata._packs"):
            load_design_ids(root)
            load_design_ids(root)
        warnings = [r for r in caplog.records if _WARNING_SNIPPET in r.message]
        assert len(warnings) <= 1, (
            f"expected at most one auto-inject warning across two loads, "
            f"got {len(warnings)}"
        )

    # frob:tests tests/unit/strata/test_packs_analyzable_warning.py::TestAnalyzableWarningDeduped.test_first_call_still_warns  # noqa: E501
    def test_first_call_still_warns(self, caplog, monkeypatch):
        """The FIRST auto-inject for a given module must still WARN --
        deduping must not silently regress to option (3), DEBUG-only."""
        monkeypatch.setattr(
            "frob.strata._packs._WARNED_ANALYZABLE_MODULES", set(), raising=True
        )
        from frob.strata import parse_module

        module = parse_module(
            """
            module sf11_first_call
            node api : trusted
            """
        ).danger_ok
        with caplog.at_level(logging.WARNING, logger="frob.strata._packs"):
            injected = require_analyzable(module)
        assert injected.is_ok
        assert any(_WARNING_SNIPPET in r.message for r in caplog.records)

    # frob:tests tests/unit/strata/test_packs_analyzable_warning.py::TestAnalyzableWarningDeduped.test_second_call_same_module_does_not_rewarn  # noqa: E501
    def test_second_call_same_module_does_not_rewarn(self, caplog, monkeypatch):
        """A repeat auto-inject for the SAME module name in the same
        process is suppressed at WARNING (the SF-11 fix)."""
        monkeypatch.setattr(
            "frob.strata._packs._WARNED_ANALYZABLE_MODULES", set(), raising=True
        )
        from frob.strata import parse_module

        module = parse_module(
            """
            module sf11_second_call
            node api : trusted
            """
        ).danger_ok
        require_analyzable(module)
        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="frob.strata._packs"):
            require_analyzable(module)
        assert not any(_WARNING_SNIPPET in r.message for r in caplog.records)
        assert "sf11_second_call" in _packs_module._WARNED_ANALYZABLE_MODULES

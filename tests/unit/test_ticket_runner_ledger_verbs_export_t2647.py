"""T-2647 regression: `_LEDGER_TRANSACTIONAL_VERBS` must be a declared
re-export (in `__all__`) of `ticket_runner/__init__.py`, not a bare
import that reads as dead code to `ruff --select F401`.

Real consumers exist outside this module (tests/test_ticket_leases.py
imports it by name), so the fix is `__all__`, not deletion -- see the
ticket body and `_ledger_mirror.py`'s own docstring for why T-2603 kept
this name as a back-compat alias. This test pins the F401-clean outcome
directly against `frob.check._python._run_ruff`, the same entrypoint
`frob check`'s lint stage uses, rather than re-deriving a subprocess
call."""

from __future__ import annotations

from pathlib import Path

from frob.check._python import _run_ruff

_TARGET = Path("src/frob/app/ticket_runner/__init__.py")


class TestLedgerTransactionalVerbsExportIsDeclared:
    """T-2647: the module's declared `__all__` re-export keeps ruff quiet
    about `_LEDGER_TRANSACTIONAL_VERBS` while preserving the name for its
    real external consumers."""

    def test_ticket_runner_init_has_no_f401_finding(self) -> None:
        # frob:tests tests/unit/test_ticket_runner_ledger_verbs_export_t2647.py::TestLedgerTransactionalVerbsExportIsDeclared.test_ticket_runner_init_has_no_f401_finding  # noqa: E501
        """Repro: before T-2647, ruff flagged `_LEDGER_TRANSACTIONAL_VERBS`
        as an unused import in this file (F401) -- a real, quarantine-
        raising finding. After T-2647 adds it to `__all__`, ruff no
        longer reports it."""
        repo_root = Path(__file__).resolve().parents[2]
        results = _run_ruff(repo_root, [str(_TARGET)], skip_format=True)
        assert len(results) == 1
        ruff_result = results[0]
        f401_diagnostics = [
            d
            for d in ruff_result.diagnostics
            if d.code == "F401" and str(_TARGET) in (d.file or "")
        ]
        assert not f401_diagnostics, (
            f"expected zero F401 findings for {_TARGET}, got: {f401_diagnostics}"
        )

    def test_ledger_transactional_verbs_still_importable_from_ticket_runner(
        self,
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_ledger_verbs_export_t2647.py::TestLedgerTransactionalVerbsExportIsDeclared.test_ledger_transactional_verbs_still_importable_from_ticket_runner  # noqa: E501
        """Positive control: the compatibility surface T-2603 deliberately
        preserved (tests/test_ticket_leases.py's own import) still
        resolves after T-2647's `__all__` change."""
        from frob.app.ticket_runner import (
            _LEDGER_TRANSACTIONAL_VERBS,
            _ticket_dispatch_table,
        )

        assert isinstance(_LEDGER_TRANSACTIONAL_VERBS, frozenset)
        assert _LEDGER_TRANSACTIONAL_VERBS
        table_verbs = frozenset(_ticket_dispatch_table().keys())
        assert _LEDGER_TRANSACTIONAL_VERBS <= table_verbs

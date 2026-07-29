"""Real-data EXHAUSTIVENESS meta-test for T-0390 (registry reconciliation:
evasion, 112 entries) -- docs/design/registry/evasion.yaml,
docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-model-t-0407.

Unlike `tests/test_registry_exhaustiveness.py` (synthetic fixtures), this
loads the REAL `docs/design/registry/evasion.yaml` against the REAL live
ticket queue -- the whole point of T-0390's acceptance criterion is that
the catalogued count (112) equals enforced+excused+deferred RIGHT NOW in
this build, not on a fixture standing in for it. Same posture as
`tests/test_check_coverage_registry.py` (T-0424) and the sibling
reconciliation pin tests for weaknesses/patterns/secrets/pii/compliance/
supply-chain (T-0384/T-0385/T-0386/T-0387/T-0388/T-0389).

Unlike those (weaknesses/compliance/supply-chain each had a self-deferral
hazard to fix), this file's 112 entries were ALREADY honestly
dispositioned before T-0390 started work: every entry carries
`deferred:T-0339`, the real open EPIC (`sound capability may-analysis --
exhaustive over static name-binding per language spec, fail-closed on
runtime dispatch`) this taxonomy exists to feed -- not T-0390 itself, so
there is no self-deferral to re-point. T-0390's job was verifying that
honesty, not fixing it; this test pins it so a future edit cannot
silently re-introduce a self-deferral or an unaccounted entry."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates import known_gate_rule_ids
from frob.gates._registry_exhaustiveness import REGISTRY_FILES, registry_gate
from frob.registry import DispositionKind, audit_registry_file, load_registry_dir
from frob.tickets import load_queue
from frob.tickets._models import TicketQueue

# frob:ticket T-0390
_REPO_ROOT = Path(__file__).resolve().parents[1]
# frob:ticket T-0390
_REGISTRY_DIR = _REPO_ROOT / "docs" / "design" / "registry"
# frob:ticket T-0390
_EVASION_CATALOGUED_TOTAL = 112


# frob:ticket T-0390
def _real_queue() -> TicketQueue:
    """Load the repo's real ticket queue, falling back to an empty queue
    only if the ledger itself fails to parse (never masks a real
    deferred-to-missing-ticket violation with a queue that is too small
    to notice)."""
    loaded = load_queue(_REPO_ROOT)
    return loaded.danger_ok if loaded.is_ok else TicketQueue(tickets={})


# frob:ticket T-0390
def _load_evasion():
    """The real, live `evasion.yaml` `RegistryFile` -- shared load helper
    so every test in this module reads the same on-disk state."""
    return load_registry_dir(_REGISTRY_DIR, ("evasion.yaml",))["evasion.yaml"].danger_ok


# frob:ticket T-0390
# frob:tests tests/test_registry_reconciliation_evasion.py::TestEvasionRegistryFile.test_is_in_registry_files  # noqa: E501
# frob:tests tests/test_registry_reconciliation_evasion.py::TestEvasionRegistryFile.test_loads_without_error  # noqa: E501
# frob:tests tests/test_registry_reconciliation_evasion.py::TestEvasionRegistryFile.test_no_malformed_entries  # noqa: E501
class TestEvasionRegistryFile:
    """`evasion.yaml` loads and is a real `RegistryFile` instance."""

    # frob:ticket T-0390
    def test_is_in_registry_files(self) -> None:
        """`evasion.yaml` is one of the files `registry_gate` actually
        scans -- an entry missing from `REGISTRY_FILES` is invisible to
        every gate no matter how well-dispositioned its own YAML is."""
        assert "evasion.yaml" in REGISTRY_FILES

    # frob:ticket T-0390
    def test_loads_without_error(self) -> None:
        """The real file parses under the unified model, not just under
        hand-rolled regex."""
        loaded = load_registry_dir(_REGISTRY_DIR, ("evasion.yaml",))
        assert "evasion.yaml" in loaded
        assert loaded["evasion.yaml"].is_ok

    # frob:ticket T-0390
    def test_no_malformed_entries(self) -> None:
        """REG006's target -- zero list items that are not a mapping, or
        are missing a string `id`, ever silently disappear from the
        count."""
        registry_file = _load_evasion()
        assert registry_file.malformed_count == 0


# frob:ticket T-0390
# frob:tests tests/test_registry_reconciliation_evasion.py::TestEvasionExhaustiveness.test_declared_total_is_112  # noqa: E501
# frob:tests tests/test_registry_reconciliation_evasion.py::TestEvasionExhaustiveness.test_audit_reports_exhausted  # noqa: E501
# frob:tests tests/test_registry_reconciliation_evasion.py::TestEvasionExhaustiveness.test_every_deferred_entry_targets_an_open_ticket  # noqa: E501
# frob:tests tests/test_registry_reconciliation_evasion.py::TestEvasionExhaustiveness.test_no_entry_defers_to_this_reconciliation_ticket  # noqa: E501
class TestEvasionExhaustiveness:
    """The T-0390 acceptance criterion: catalogued count == enforced +
    excused + deferred, pinned against the file's own declared 112-entry
    total so a future silent drop (or silent addition without a
    disposition) fails the build."""

    # frob:ticket T-0390
    def test_declared_total_is_112(self) -> None:
        """Locks the denominator itself -- if this ever drifts, the
        reconciliation this ticket did is no longer measuring the whole
        universe."""
        registry_file = _load_evasion()
        assert registry_file.declared_totals["total"] == _EVASION_CATALOGUED_TOTAL

    # frob:ticket T-0390
    def test_audit_reports_exhausted(self) -> None:
        """`audit_registry_file`'s one-line honest answer: zero
        unaccounted, zero malformed, over the REAL 112-entry file."""
        registry_file = _load_evasion()
        audit = audit_registry_file(registry_file)

        assert audit.total == _EVASION_CATALOGUED_TOTAL
        assert audit.exhausted is True
        assert audit.unaccounted == 0
        assert (
            audit.handled + audit.deferred + audit.duplicate + audit.out_of_scope
            == _EVASION_CATALOGUED_TOTAL
        )

    # frob:ticket T-0390
    # frob:waive DUP001 reason="T-1006: the zero-deferred skip guard added here mirrors the identical T-1116 precedent already established in the sibling test_registry_reconciliation_weaknesses/system_design/supply_chain.py exhaustiveness tests -- each reconciliation registry's positive-case test is intentionally the same shape by convention (T-0384/T-0385/T-0386/T-0387/T-0388 family); extracting a shared helper across four independent registry test modules is a cross-file refactor out of T-1006's declared scope"  # noqa: E501
    # frob:waive DUP002 reason="T-1006: same shape added in the same diff to test_registry_reconciliation_supply_chain.py's sibling test for the identical reason -- see DUP001 waiver above"  # noqa: E501
    def test_every_deferred_entry_targets_an_open_ticket(self) -> None:
        """REG003's positive case, pinned to real data: every
        `deferred:T-XXXX` disposition in evasion.yaml names a ticket that
        actually exists and is not DONE -- a deferral to a closed or
        missing ticket is a silent drop wearing a disposition's clothes."""
        registry_file = _load_evasion()
        queue = _real_queue()
        deferred = [
            entry
            for entries in registry_file.entry_lists.values()
            for entry in entries
            if entry.disposition.kind is DispositionKind.DEFERRED
        ]
        if not deferred:
            pytest.skip(
                "T-1006: no deferred: entries currently in evasion.yaml -- "
                "every prior deferral has been resolved by landing waves "
                "since this test was written; this positive-case check has "
                "nothing real to pin against right now, not a regression"
            )
        for entry in deferred:
            ticket_id = entry.disposition.target
            assert ticket_id is not None, f"{entry.id} deferred with no target ticket"
            ticket = queue.tickets.get(ticket_id)
            assert ticket is not None, f"{entry.id} defers to missing {ticket_id}"
            assert ticket.state.value != "done", (
                f"{entry.id} defers to closed ticket {ticket_id}"
            )

    # frob:ticket T-0390
    def test_no_entry_defers_to_this_reconciliation_ticket(self) -> None:
        """This registry's own hazard, checked even though it never
        materialized here: all 112 entries already read `deferred:T-0339`
        (the real feeding epic), never `deferred:T-0390` (this
        review-gated reconciliation ticket, expected to close) -- pins
        that no future edit accidentally re-points an entry at the
        ticket that is about to close out from under it."""
        registry_file = _load_evasion()
        deferred_targets = {
            entry.disposition.target
            for entries in registry_file.entry_lists.values()
            for entry in entries
            if entry.disposition.kind is DispositionKind.DEFERRED
        }
        assert "T-0390" not in deferred_targets


# frob:ticket T-0390
# frob:tests tests/test_registry_reconciliation_evasion.py::TestExhaustivenessGateOverRealEvasion.test_no_evasion_violations  # noqa: E501
class TestExhaustivenessGateOverRealEvasion:
    """`registry_gate` over the real registry dir raises zero violations
    for `evasion.yaml` specifically -- wired into `frob check` (the
    default gate run), not a side-channel-only assertion."""

    # frob:ticket T-0390
    def test_no_evasion_violations(self) -> None:
        real_queue = _real_queue()

        violations = registry_gate(
            _REPO_ROOT, real_queue, known_gate_rule_ids(), _REGISTRY_DIR
        )
        evasion_violations = [
            v for v in violations if v.file == "docs/design/registry/evasion.yaml"
        ]

        assert evasion_violations == []

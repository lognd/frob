"""Real-data EXHAUSTIVENESS meta-test for T-0388/T-0607 (registry
reconciliation: compliance, 27 entries) -- docs/design/registry/
compliance.yaml, docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-
model-t-0407.

Unlike `tests/test_registry_exhaustiveness.py` (synthetic fixtures), this
loads the REAL `docs/design/registry/compliance.yaml` against the REAL
live ticket queue -- the whole point of T-0388's acceptance criterion is
that the catalogued count (27) equals enforced+excused+deferred RIGHT NOW
in this build, not on a fixture standing in for it. Same posture as
`tests/test_check_coverage_registry.py` (T-0424) and the sibling
reconciliation pin tests for patterns/secrets/pii (T-0385/T-0386/T-0387).

Unlike those three, this file's entries were NOT already fully
dispositioned honestly: 17 of 27 originally carried `deferred:T-0388`,
which is T-0388 itself (a review-gated reconciliation ticket expected to
close) -- deferring to the closing ticket would break REG003 (deferred-
to-closed-ticket) the moment it closes. T-0388 re-pointed those 17
entries to a newly filed ticket, T-0607, as a stopgap; T-0607 then closed
the loop for real (rather than repeating the same self-reference hazard
one ticket later): each of the 17 now carries a reasoned `out_of_scope`
disposition backed by a real standing structural check (COMPLIANCE005,
`_check_cmpl_registry_unit_dispositions` in `src/frob/strata/
_compliance.py`) instead of a `deferred:` promise to some future ticket.
`compliance.yaml` therefore carries ZERO `deferred:` entries as of
T-0607 -- the positive `deferred:` fixture test below now asserts that
absence directly rather than requiring at least one to exist."""

from __future__ import annotations

from pathlib import Path

from frob.gates import known_gate_rule_ids
from frob.gates._registry_exhaustiveness import REGISTRY_FILES, registry_gate
from frob.registry import DispositionKind, audit_registry_file, load_registry_dir
from frob.tickets import load_queue
from frob.tickets._models import TicketQueue

# frob:ticket T-0388
_REPO_ROOT = Path(__file__).resolve().parents[1]
# frob:ticket T-0388
_REGISTRY_DIR = _REPO_ROOT / "docs" / "design" / "registry"
# frob:ticket T-0388
_COMPLIANCE_CATALOGUED_TOTAL = 27


# frob:ticket T-0388
def _real_queue() -> TicketQueue:
    """Load the repo's real ticket queue, falling back to an empty queue
    only if the ledger itself fails to parse (never masks a real
    deferred-to-missing-ticket violation with a queue that is too small
    to notice)."""
    loaded = load_queue(_REPO_ROOT)
    return loaded.danger_ok if loaded.is_ok else TicketQueue(tickets={})


# frob:ticket T-0388
# frob:tests tests/test_registry_reconciliation_compliance.py::TestComplianceRegistryFile.test_is_in_registry_files
# frob:tests tests/test_registry_reconciliation_compliance.py::TestComplianceRegistryFile.test_loads_without_error
# frob:tests tests/test_registry_reconciliation_compliance.py::TestComplianceRegistryFile.test_no_malformed_entries
class TestComplianceRegistryFile:
    """`compliance.yaml` loads and is a real `RegistryFile` instance."""

    # frob:ticket T-0388
    def test_is_in_registry_files(self) -> None:
        """`compliance.yaml` is one of the files `registry_gate` actually
        scans -- an entry missing from `REGISTRY_FILES` is invisible to
        every gate no matter how well-dispositioned its own YAML is."""
        assert "compliance.yaml" in REGISTRY_FILES

    # frob:ticket T-0388
    def test_loads_without_error(self) -> None:
        """The real file parses under the unified model, not just under
        hand-rolled regex."""
        loaded = load_registry_dir(_REGISTRY_DIR, ("compliance.yaml",))
        assert "compliance.yaml" in loaded
        assert loaded["compliance.yaml"].is_ok

    # frob:ticket T-0388
    def test_no_malformed_entries(self) -> None:
        """REG006's target -- zero list items that are not a mapping, or
        are missing a string `id`, ever silently disappear from the
        count."""
        registry_file = load_registry_dir(_REGISTRY_DIR, ("compliance.yaml",))[
            "compliance.yaml"
        ].danger_ok
        assert registry_file.malformed_count == 0


# frob:ticket T-0388
# frob:tests tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness.test_declared_total_is_27
# frob:tests tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness.test_audit_reports_exhausted
# frob:tests tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness.test_every_deferred_entry_targets_an_open_ticket
# frob:tests tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness.test_no_entry_defers_to_this_reconciliation_ticket
# frob:tests tests/test_registry_reconciliation_compliance.py::TestComplianceExhaustiveness.test_cmpl_registry_units_carry_handled_by_or_out_of_scope
class TestComplianceExhaustiveness:
    """The T-0388 acceptance criterion: catalogued count == enforced +
    excused + deferred, pinned against the file's own declared 27-entry
    total so a future silent drop (or silent addition without a
    disposition) fails the build."""

    # frob:ticket T-0388
    def test_declared_total_is_27(self) -> None:
        """Locks the denominator itself -- if this ever drifts, the
        reconciliation this ticket did is no longer measuring the whole
        universe."""
        registry_file = load_registry_dir(_REGISTRY_DIR, ("compliance.yaml",))[
            "compliance.yaml"
        ].danger_ok
        assert registry_file.declared_totals["total"] == _COMPLIANCE_CATALOGUED_TOTAL

    # frob:ticket T-0388
    def test_audit_reports_exhausted(self) -> None:
        """`audit_registry_file`'s one-line honest answer: zero
        unaccounted, zero malformed, over the REAL 27-entry file."""
        registry_file = load_registry_dir(_REGISTRY_DIR, ("compliance.yaml",))[
            "compliance.yaml"
        ].danger_ok
        audit = audit_registry_file(registry_file)

        assert audit.total == _COMPLIANCE_CATALOGUED_TOTAL
        assert audit.exhausted is True
        assert audit.unaccounted == 0
        assert (
            audit.handled + audit.deferred + audit.duplicate + audit.out_of_scope
            == (_COMPLIANCE_CATALOGUED_TOTAL)
        )

    # frob:ticket T-0607
    def test_every_deferred_entry_targets_an_open_ticket(self) -> None:
        """REG003's positive case, pinned to real data: every
        `deferred:T-XXXX` disposition in compliance.yaml names a ticket
        that actually exists and is not DONE -- a deferral to a closed or
        missing ticket is a silent drop wearing a disposition's clothes.
        As of T-0607, compliance.yaml carries ZERO `deferred:` entries
        (all 17 formerly-deferred units now carry a reasoned
        `out_of_scope` disposition backed by COMPLIANCE005's standing
        structural check) -- this loop body is vacuously true, and the
        emptiness itself is asserted rather than requiring a fixture."""
        registry_file = load_registry_dir(_REGISTRY_DIR, ("compliance.yaml",))[
            "compliance.yaml"
        ].danger_ok
        queue = _real_queue()
        deferred = [
            entry
            for entries in registry_file.entry_lists.values()
            for entry in entries
            if entry.disposition.kind is DispositionKind.DEFERRED
        ]
        assert deferred == [], (
            "T-0607 flipped every CMPL-* unit off deferred: -- a new "
            "deferred entry here needs the same handled_by/out_of_scope "
            "treatment, not a silent reintroduction"
        )
        for entry in deferred:
            ticket_id = entry.disposition.target
            assert ticket_id is not None, f"{entry.id} deferred with no target ticket"
            ticket = queue.tickets.get(ticket_id)
            assert ticket is not None, f"{entry.id} defers to missing {ticket_id}"
            assert ticket.state.value != "done", (
                f"{entry.id} defers to closed ticket {ticket_id}"
            )

    # frob:ticket T-0607
    def test_no_entry_defers_to_this_reconciliation_ticket(self) -> None:
        """This registry's own hazard, caught honestly rather than
        pinned around: 17 entries originally read `deferred:T-0388`, then
        `deferred:T-0607` -- both self-references to the very ticket
        doing the reconciliation, which would silently expire the moment
        that ticket closed. Locks that NEITHER re-pointing stuck: no
        entry defers to T-0388 or T-0607 anymore (T-0607 replaced the
        deferral with a real out_of_scope disposition, not a third
        ticket to defer to)."""
        registry_file = load_registry_dir(_REGISTRY_DIR, ("compliance.yaml",))[
            "compliance.yaml"
        ].danger_ok
        deferred_targets = {
            entry.disposition.target
            for entries in registry_file.entry_lists.values()
            for entry in entries
            if entry.disposition.kind is DispositionKind.DEFERRED
        }
        assert "T-0388" not in deferred_targets
        assert "T-0607" not in deferred_targets

    # frob:ticket T-0607
    def test_cmpl_registry_units_carry_handled_by_or_out_of_scope(self) -> None:
        """The T-0607 acceptance criterion in code form: every one of the
        17 `CMPL_REGISTRY_UNIT_IDS` units now carries `handled_by` or
        `out_of_scope`, verified against the REAL file -- the same
        property `check_cmpl_registry` (COMPLIANCE005) enforces going
        forward, pinned here against today's real data too."""
        from frob.strata._compliance import (
            CMPL_REGISTRY_UNIT_IDS,
            check_cmpl_registry,
        )

        result = check_cmpl_registry(_REGISTRY_DIR)
        assert result.is_ok
        assert result.danger_ok == ()

        registry_file = load_registry_dir(_REGISTRY_DIR, ("compliance.yaml",))[
            "compliance.yaml"
        ].danger_ok
        by_id = {
            entry.id: entry
            for entries in registry_file.entry_lists.values()
            for entry in entries
        }
        for unit_id in CMPL_REGISTRY_UNIT_IDS:
            assert unit_id in by_id, f"{unit_id} missing from compliance.yaml"
            assert by_id[unit_id].disposition.kind in (
                DispositionKind.HANDLED_BY,
                DispositionKind.OUT_OF_SCOPE,
            )


# frob:ticket T-0388
# frob:tests tests/test_registry_reconciliation_compliance.py::TestExhaustivenessGateOverRealCompliance.test_no_compliance_violations
class TestExhaustivenessGateOverRealCompliance:
    """`registry_gate` over the real registry dir raises zero violations
    for `compliance.yaml` specifically -- wired into `frob check` (the
    default gate run), not a side-channel-only assertion."""

    # frob:ticket T-0388
    def test_no_compliance_violations(self) -> None:
        real_queue = _real_queue()

        violations = registry_gate(
            _REPO_ROOT, real_queue, known_gate_rule_ids(), _REGISTRY_DIR
        )
        compliance_violations = [
            v for v in violations if v.file == "docs/design/registry/compliance.yaml"
        ]

        assert compliance_violations == []

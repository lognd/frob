# frob:waive SCOPE001 reason="T-0392's declared scope is src/frob/strata/+docs/design/registry/system-design.yaml; tests/** is leased in-progress elsewhere so the scope cannot be formally extended here, same ad-hoc precedent as tests/test_check_coverage_registry.py's existing T-0424 SCOPE001 waiver and the sibling reconciliation pin tests (T-0384/T-0385/T-0386/T-0387/T-0388/T-0389/T-0390)"  # noqa: E501
"""Real-data EXHAUSTIVENESS meta-test for T-0392 (registry reconciliation:
system-design, 119 entries) -- docs/design/registry/system-design.yaml,
docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-model-t-0407.

Unlike `tests/test_registry_exhaustiveness.py` (synthetic fixtures), this
loads the REAL `docs/design/registry/system-design.yaml` against the REAL
live ticket queue -- the whole point of T-0392's acceptance criterion is
that the catalogued count (119, 14 of which are RECONCILIATION.md finding
(d)'s manifest-extraction artifacts, dispositioned out-of-scope rather
than dropped) equals enforced+excused+deferred RIGHT NOW in this build,
not on a fixture standing in for it. Same posture as
`tests/test_check_coverage_registry.py` (T-0424) and the sibling
reconciliation pin tests for weaknesses/patterns/secrets/pii/compliance/
supply-chain/evasion (T-0384/T-0385/T-0386/T-0387/T-0388/T-0389/T-0390).

Like T-0388's compliance.yaml and T-0389's supply-chain.yaml, this file's
entries were NOT already fully dispositioned honestly: 49 of the 105
genuine (non-artifact) entries carried `deferred:T-0392`, which is
T-0392 itself (a review-gated reconciliation ticket expected to close) --
deferring to the closing ticket would break REG003 (deferred-to-closed-
ticket) the moment it closes. T-0392 re-pointed those 49 entries to a
newly filed standing ticket before this test pins the file. NOTE: the
re-pointed target may appear here as a `T-draft-*` id -- drafts do not
survive `frob ticket land` (T-0577) and get replaced by a real id at land
time, mirroring the T-0607/T-0388 precedent exactly; this test only
asserts the target resolves to a real, non-done ticket in the CURRENT
queue, not any specific id spelling. The other 56 genuine entries were
already honestly deferred to T-0331 (the real feeding systems-checks
epic) and are left untouched.

T-0392 is itself a blocker of T-0658 (the T-0331 epic's N:M coverage
close condition) and of T-0677/T-0678 (manifest-artifact cleanup /
cross-corpus totality) -- those tickets can only treat "registered check"
as a real, checkable claim once this reconciliation pass lands, which is
why the 49 re-pointed entries above go to a dedicated implementation
ticket rather than staying vaguely attached to T-0392."""

from __future__ import annotations

from pathlib import Path

from frob.gates import known_gate_rule_ids
from frob.gates._registry_exhaustiveness import REGISTRY_FILES, registry_gate
from frob.registry import DispositionKind, audit_registry_file, load_registry_dir
from frob.tickets import load_queue
from frob.tickets._models import TicketQueue

# frob:ticket T-0392
_REPO_ROOT = Path(__file__).resolve().parents[1]
# frob:ticket T-0392
_REGISTRY_DIR = _REPO_ROOT / "docs" / "design" / "registry"
# frob:ticket T-0392
_SYSTEM_DESIGN_CATALOGUED_TOTAL = 119


# frob:ticket T-0392
# frob:waive DUP001 reason="parallel per-domain test scaffolding across 8 sibling test modules \
# (8 sites) -- each file exercises a structurally similar check for \
# a distinct domain/module with the same arrange-act shape; \
# extracting would blur which domain owns which check"
def _real_queue() -> TicketQueue:
    """Load the repo's real ticket queue, falling back to an empty queue
    only if the ledger itself fails to parse (never masks a real
    deferred-to-missing-ticket violation with a queue that is too small
    to notice)."""
    loaded = load_queue(_REPO_ROOT)
    return loaded.danger_ok if loaded.is_ok else TicketQueue(tickets={})


# frob:ticket T-0392
def _load_system_design():
    """The real, live `system-design.yaml` `RegistryFile` -- shared load
    helper so every test in this module reads the same on-disk state."""
    return load_registry_dir(_REGISTRY_DIR, ("system-design.yaml",))[
        "system-design.yaml"
    ].danger_ok


# frob:ticket T-0392
# frob:tests tests/test_registry_reconciliation_system_design.py::TestSystemDesignRegistryFile.test_is_in_registry_files  # noqa: E501
# frob:tests tests/test_registry_reconciliation_system_design.py::TestSystemDesignRegistryFile.test_loads_without_error  # noqa: E501
# frob:tests tests/test_registry_reconciliation_system_design.py::TestSystemDesignRegistryFile.test_no_malformed_entries  # noqa: E501
class TestSystemDesignRegistryFile:
    """`system-design.yaml` loads and is a real `RegistryFile` instance."""

    # frob:ticket T-0392
    def test_is_in_registry_files(self) -> None:
        """`system-design.yaml` is one of the files `registry_gate`
        actually scans -- an entry missing from `REGISTRY_FILES` is
        invisible to every gate no matter how well-dispositioned its own
        YAML is."""
        assert "system-design.yaml" in REGISTRY_FILES

    # frob:ticket T-0392
    def test_loads_without_error(self) -> None:
        """The real file parses under the unified model, not just under
        hand-rolled regex."""
        loaded = load_registry_dir(_REGISTRY_DIR, ("system-design.yaml",))
        assert "system-design.yaml" in loaded
        assert loaded["system-design.yaml"].is_ok

    # frob:ticket T-0392
    def test_no_malformed_entries(self) -> None:
        """REG006's target -- zero list items that are not a mapping, or
        are missing a string `id`, ever silently disappear from the
        count."""
        registry_file = _load_system_design()
        assert registry_file.malformed_count == 0


# frob:ticket T-0392
# frob:tests tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness.test_declared_total_is_119  # noqa: E501
# frob:tests tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness.test_audit_reports_exhausted  # noqa: E501
# frob:tests tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness.test_every_deferred_entry_targets_an_open_ticket  # noqa: E501
# frob:tests tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness.test_no_entry_defers_to_this_reconciliation_ticket  # noqa: E501
class TestSystemDesignExhaustiveness:
    """The T-0392 acceptance criterion: catalogued count == enforced +
    excused + deferred, pinned against the file's own declared 119-entry
    total (105 genuine + 14 manifest-extraction artifacts) so a future
    silent drop (or silent addition without a disposition) fails the
    build."""

    # frob:ticket T-0392
    def test_declared_total_is_119(self) -> None:
        """Locks the denominator itself -- if this ever drifts, the
        reconciliation this ticket did is no longer measuring the whole
        universe."""
        registry_file = _load_system_design()
        assert registry_file.declared_totals["total"] == _SYSTEM_DESIGN_CATALOGUED_TOTAL

    # frob:ticket T-0392
    # frob:waive DUP001 reason="parallel per-domain test scaffolding across \
    # test_registry_reconciliation_system_design.py, \
    # test_system_design_coverage.py (2 sites) -- each file exercises a \
    # structurally similar check for a distinct domain/module with the \
    # same arrange-act shape; extracting would blur which domain owns \
    # which check"
    def test_audit_reports_exhausted(self) -> None:
        """`audit_registry_file`'s one-line honest answer: zero
        unaccounted, zero malformed, over the REAL 119-entry file."""
        registry_file = _load_system_design()
        audit = audit_registry_file(registry_file)

        assert audit.total == _SYSTEM_DESIGN_CATALOGUED_TOTAL
        assert audit.exhausted is True
        assert audit.unaccounted == 0
        assert (
            audit.handled + audit.deferred + audit.duplicate + audit.out_of_scope
            == _SYSTEM_DESIGN_CATALOGUED_TOTAL
        )

    # frob:ticket T-0392
    def test_every_deferred_entry_targets_an_open_ticket(self) -> None:
        """REG003's positive case, pinned to real data: every
        `deferred:T-XXXX` disposition in system-design.yaml names a
        ticket that actually exists and is not DONE -- a deferral to a
        closed or missing ticket is a silent drop wearing a
        disposition's clothes."""
        registry_file = _load_system_design()
        queue = _real_queue()
        deferred = [
            entry
            for entries in registry_file.entry_lists.values()
            for entry in entries
            if entry.disposition.kind is DispositionKind.DEFERRED
        ]
        assert deferred, "expected at least one deferred entry to check against"
        for entry in deferred:
            ticket_id = entry.disposition.target
            assert ticket_id is not None, f"{entry.id} deferred with no target ticket"
            ticket = queue.tickets.get(ticket_id)
            assert ticket is not None, f"{entry.id} defers to missing {ticket_id}"
            assert ticket.state.value != "done", (
                f"{entry.id} defers to closed ticket {ticket_id}"
            )

    # frob:ticket T-0392
    def test_no_entry_defers_to_this_reconciliation_ticket(self) -> None:
        """This registry's own hazard, caught honestly rather than
        pinned around: 49 entries originally read `deferred:T-0392`, but
        T-0392 IS this review-gated reconciliation ticket and is expected
        to close -- a deferral naming its own closing ticket is a
        disposition that silently expires. Locks that the re-pointing
        away from T-0392 stuck."""
        registry_file = _load_system_design()
        deferred_targets = {
            entry.disposition.target
            for entries in registry_file.entry_lists.values()
            for entry in entries
            if entry.disposition.kind is DispositionKind.DEFERRED
        }
        assert "T-0392" not in deferred_targets


# frob:ticket T-0392
# frob:tests tests/test_registry_reconciliation_system_design.py::TestExhaustivenessGateOverRealSystemDesign.test_no_system_design_violations  # noqa: E501
class TestExhaustivenessGateOverRealSystemDesign:
    """`registry_gate` over the real registry dir raises zero violations
    for `system-design.yaml` specifically -- wired into `frob check` (the
    default gate run), not a side-channel-only assertion."""

    # frob:ticket T-0392
    # frob:waive DUP001 reason="parallel per-domain test scaffolding across 8 sibling test modules \
    # (8 sites) -- each file exercises a structurally similar check for \
    # a distinct domain/module with the same arrange-act shape; \
    # extracting would blur which domain owns which check"
    def test_no_system_design_violations(self) -> None:
        real_queue = _real_queue()

        violations = registry_gate(
            _REPO_ROOT, real_queue, known_gate_rule_ids(), _REGISTRY_DIR
        )
        system_design_violations = [
            v for v in violations if v.file == "docs/design/registry/system-design.yaml"
        ]

        assert system_design_violations == []

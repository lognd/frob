"""Real-data EXHAUSTIVENESS meta-test for T-0384 (registry reconciliation:
weaknesses, 944 CWEs + 40 other-framework entries = 984 total) --
docs/design/registry/weaknesses.yaml,
docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-model-t-0407.

Unlike `tests/test_registry_exhaustiveness.py` (synthetic fixtures), this
loads the REAL `docs/design/registry/weaknesses.yaml` against the REAL
live ticket queue -- the whole point of T-0384's acceptance criterion is
that the catalogued count (984, of which 944 are the MITRE CWE-1000 View
entries) equals enforced+excused+deferred RIGHT NOW in this build, not on
a fixture standing in for it. Same posture as
`tests/test_check_coverage_registry.py` (T-0424) and the sibling
reconciliation pin tests for patterns/secrets/pii/compliance
(T-0385/T-0386/T-0387/T-0388).

Like T-0388's compliance.yaml, this file's entries were NOT already fully
dispositioned honestly: all 27 `deferred:` entries carried
`deferred:T-0384`, which is T-0384 itself (a review-gated reconciliation
ticket expected to close) -- deferring to the closing ticket would break
REG003 (deferred-to-closed-ticket) the moment it closes. T-0384 re-pointed
those 27 entries (CWE-20/22/77/78/79/89/94/119/125/190/269/276/287/306/
352/362/416/434/476/502/639/787/798/862/863/918/922 -- overlapping the
CWE Top-25/OWASP classic set, relevant to T-0674's Top-25 tension
follow-up) to a newly filed standing ticket before this test pins the
file. NOTE: the re-pointed target may appear here as a `T-draft-*` id --
drafts do not survive `frob ticket land` (T-0577) and get replaced by a
real id at land time, mirroring the T-0607/T-0388 precedent exactly; this
test only asserts the target resolves to a real, non-done ticket in the
CURRENT queue, not any specific id spelling.
"""

from __future__ import annotations

from pathlib import Path

from frob.gates import known_gate_rule_ids
from frob.gates._registry_exhaustiveness import REGISTRY_FILES, registry_gate
from frob.registry import DispositionKind, audit_registry_file, load_registry_dir
from frob.tickets import load_queue
from frob.tickets._models import TicketQueue

# frob:ticket T-0384
_REPO_ROOT = Path(__file__).resolve().parents[1]
# frob:ticket T-0384
_REGISTRY_DIR = _REPO_ROOT / "docs" / "design" / "registry"
# frob:ticket T-0384
_WEAKNESSES_CATALOGUED_TOTAL = 984
# frob:ticket T-0384
_WEAKNESSES_CWE_TOTAL = 944


# frob:ticket T-0384
def _real_queue() -> TicketQueue:
    """Load the repo's real ticket queue, falling back to an empty queue
    only if the ledger itself fails to parse (never masks a real
    deferred-to-missing-ticket violation with a queue that is too small
    to notice)."""
    loaded = load_queue(_REPO_ROOT)
    return loaded.danger_ok if loaded.is_ok else TicketQueue(tickets={})


# frob:ticket T-0384
def _load_weaknesses():
    """The real, live `weaknesses.yaml` `RegistryFile` -- shared load
    helper so every test in this module reads the same on-disk state."""
    return load_registry_dir(_REGISTRY_DIR, ("weaknesses.yaml",))[
        "weaknesses.yaml"
    ].danger_ok


# frob:ticket T-0384
# frob:tests tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesRegistryFile.test_is_in_registry_files  # noqa: E501
# frob:tests tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesRegistryFile.test_loads_without_error  # noqa: E501
# frob:tests tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesRegistryFile.test_no_malformed_entries  # noqa: E501
class TestWeaknessesRegistryFile:
    """`weaknesses.yaml` loads and is a real `RegistryFile` instance."""

    # frob:ticket T-0384
    def test_is_in_registry_files(self) -> None:
        """`weaknesses.yaml` is one of the files `registry_gate` actually
        scans -- an entry missing from `REGISTRY_FILES` is invisible to
        every gate no matter how well-dispositioned its own YAML is."""
        assert "weaknesses.yaml" in REGISTRY_FILES

    # frob:ticket T-0384
    def test_loads_without_error(self) -> None:
        """The real file parses under the unified model, not just under
        hand-rolled regex."""
        loaded = load_registry_dir(_REGISTRY_DIR, ("weaknesses.yaml",))
        assert "weaknesses.yaml" in loaded
        assert loaded["weaknesses.yaml"].is_ok

    # frob:ticket T-0384
    def test_no_malformed_entries(self) -> None:
        """REG006's target -- zero list items that are not a mapping, or
        are missing a string `id`, ever silently disappear from the
        count, across BOTH `cwe_entries` and
        `other_weakness_framework_entries`."""
        registry_file = _load_weaknesses()
        assert registry_file.malformed_count == 0


# frob:ticket T-0384
# frob:tests tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness.test_declared_cwe_total_is_944  # noqa: E501
# frob:tests tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness.test_audit_reports_exhausted  # noqa: E501
# frob:tests tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness.test_every_deferred_entry_targets_an_open_ticket  # noqa: E501
# frob:tests tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness.test_no_entry_defers_to_this_reconciliation_ticket  # noqa: E501
class TestWeaknessesExhaustiveness:
    """The T-0384 acceptance criterion: catalogued count == enforced +
    excused + deferred, pinned against the file's own declared 944-CWE
    total (and the observed 984 grand total across both entry lists) so a
    future silent drop (or silent addition without a disposition) fails
    the build."""

    # frob:ticket T-0384
    def test_declared_cwe_total_is_944(self) -> None:
        """Locks the CWE-1000-View denominator itself (`cwe_total:` in
        the YAML, the only per-list total this file's loader captures) --
        if this ever drifts, the reconciliation this ticket did is no
        longer measuring the whole MITRE view."""
        registry_file = _load_weaknesses()
        assert registry_file.declared_totals["cwe_total"] == _WEAKNESSES_CWE_TOTAL

    # frob:ticket T-0384
    def test_audit_reports_exhausted(self) -> None:
        """`audit_registry_file`'s one-line honest answer: zero
        unaccounted, zero malformed, over the REAL 984-entry file (944
        CWE + 40 other-framework entries -- both entry lists this file
        declares)."""
        registry_file = _load_weaknesses()
        audit = audit_registry_file(registry_file)

        assert audit.total == _WEAKNESSES_CATALOGUED_TOTAL
        assert audit.exhausted is True
        assert audit.unaccounted == 0
        assert (
            audit.handled + audit.deferred + audit.duplicate + audit.out_of_scope
            == _WEAKNESSES_CATALOGUED_TOTAL
        )

    # frob:ticket T-0384
    def test_every_deferred_entry_targets_an_open_ticket(self) -> None:
        """REG003's positive case, pinned to real data: every
        `deferred:T-XXXX` disposition in weaknesses.yaml names a ticket
        that actually exists and is not DONE -- a deferral to a closed or
        missing ticket is a silent drop wearing a disposition's clothes."""
        registry_file = _load_weaknesses()
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

    # frob:ticket T-0384
    def test_no_entry_defers_to_this_reconciliation_ticket(self) -> None:
        """This registry's own hazard, caught honestly rather than
        pinned around: all 27 deferred entries originally read
        `deferred:T-0384`, but T-0384 IS this review-gated reconciliation
        ticket and is expected to close -- a deferral naming its own
        closing ticket is a disposition that silently expires. Locks
        that the re-pointing away from T-0384 stuck."""
        registry_file = _load_weaknesses()
        deferred_targets = {
            entry.disposition.target
            for entries in registry_file.entry_lists.values()
            for entry in entries
            if entry.disposition.kind is DispositionKind.DEFERRED
        }
        assert "T-0384" not in deferred_targets


# frob:ticket T-0384
# frob:tests tests/test_registry_reconciliation_weaknesses.py::TestExhaustivenessGateOverRealWeaknesses.test_no_weaknesses_violations  # noqa: E501
class TestExhaustivenessGateOverRealWeaknesses:
    """`registry_gate` over the real registry dir raises zero violations
    for `weaknesses.yaml` specifically -- wired into `frob check` (the
    default gate run), not a side-channel-only assertion."""

    # frob:ticket T-0384
    def test_no_weaknesses_violations(self) -> None:
        real_queue = _real_queue()

        violations = registry_gate(
            _REPO_ROOT, real_queue, known_gate_rule_ids(), _REGISTRY_DIR
        )
        weaknesses_violations = [
            v for v in violations if v.file == "docs/design/registry/weaknesses.yaml"
        ]

        assert weaknesses_violations == []

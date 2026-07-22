# frob:waive SCOPE001 reason="T-0386's declared scope is src/frob/vet/+docs/design/registry/secrets.yaml; tests/** is leased in-progress by T-0160 so the scope cannot be formally extended here, same ad-hoc precedent as tests/test_check_coverage_registry.py's existing T-0424 SCOPE001 waiver"  # noqa: E501
"""Real-data EXHAUSTIVENESS meta-test for T-0386 (registry reconciliation:
secrets, 3 entries) -- docs/design/registry/secrets.yaml,
docs/design/registry/EXHAUSTIVENESS-GATE.md#unified-model-t-0407.

Unlike `tests/test_registry_exhaustiveness.py` (synthetic fixtures), this
loads the REAL `docs/design/registry/secrets.yaml` against the REAL live
ticket queue -- the whole point of T-0386's acceptance criterion is that
the catalogued count (3) equals enforced+excused+deferred RIGHT NOW in
this build, not on a fixture standing in for it. Same posture as
`tests/test_check_coverage_registry.py` (T-0424) and
`tests/test_registry_reconciliation_patterns.py` (T-0385)."""

from __future__ import annotations

from pathlib import Path

from frob.gates import known_gate_rule_ids
from frob.gates._registry_exhaustiveness import REGISTRY_FILES, registry_gate
from frob.registry import DispositionKind, audit_registry_file, load_registry_dir
from frob.tickets import load_queue
from frob.tickets._models import TicketQueue

# frob:ticket T-0386
_REPO_ROOT = Path(__file__).resolve().parents[1]
# frob:ticket T-0386
_REGISTRY_DIR = _REPO_ROOT / "docs" / "design" / "registry"
# frob:ticket T-0386
_SECRETS_CATALOGUED_TOTAL = 3


# frob:ticket T-0386
def _real_queue() -> TicketQueue:
    """Load the repo's real ticket queue, falling back to an empty queue
    only if the ledger itself fails to parse (never masks a real
    deferred-to-missing-ticket violation with a queue that is too small
    to notice)."""
    loaded = load_queue(_REPO_ROOT)
    return loaded.danger_ok if loaded.is_ok else TicketQueue(tickets={})


# frob:ticket T-0386
# frob:tests tests/test_registry_reconciliation_secrets.py::TestSecretsRegistryFile.test_is_in_registry_files
# frob:tests tests/test_registry_reconciliation_secrets.py::TestSecretsRegistryFile.test_loads_without_error
# frob:tests tests/test_registry_reconciliation_secrets.py::TestSecretsRegistryFile.test_no_malformed_entries
class TestSecretsRegistryFile:
    """`secrets.yaml` loads and is a real `RegistryFile` instance."""

    # frob:ticket T-0386
    def test_is_in_registry_files(self) -> None:
        """`secrets.yaml` is one of the files `registry_gate` actually
        scans -- an entry missing from `REGISTRY_FILES` is invisible to
        every gate no matter how well-dispositioned its own YAML is."""
        assert "secrets.yaml" in REGISTRY_FILES

    # frob:ticket T-0386
    def test_loads_without_error(self) -> None:
        """The real file parses under the unified model, not just under
        hand-rolled regex."""
        loaded = load_registry_dir(_REGISTRY_DIR, ("secrets.yaml",))
        assert "secrets.yaml" in loaded
        assert loaded["secrets.yaml"].is_ok

    # frob:ticket T-0386
    def test_no_malformed_entries(self) -> None:
        """REG006's target -- zero list items that are not a mapping, or
        are missing a string `id`, ever silently disappear from the
        count."""
        registry_file = load_registry_dir(_REGISTRY_DIR, ("secrets.yaml",))[
            "secrets.yaml"
        ].danger_ok
        assert registry_file.malformed_count == 0


# frob:ticket T-0386
# frob:tests tests/test_registry_reconciliation_secrets.py::TestSecretsExhaustiveness.test_declared_total_is_3
# frob:tests tests/test_registry_reconciliation_secrets.py::TestSecretsExhaustiveness.test_audit_reports_exhausted
# frob:tests tests/test_registry_reconciliation_secrets.py::TestSecretsExhaustiveness.test_every_deferred_entry_targets_an_open_ticket
class TestSecretsExhaustiveness:
    """The T-0386 acceptance criterion: catalogued count == enforced +
    excused + deferred, pinned against the file's own declared 3-entry
    total so a future silent drop (or silent addition without a
    disposition) fails the build."""

    # frob:ticket T-0386
    def test_declared_total_is_3(self) -> None:
        """Locks the denominator itself -- if this ever drifts, the
        reconciliation this ticket did is no longer measuring the whole
        universe."""
        registry_file = load_registry_dir(_REGISTRY_DIR, ("secrets.yaml",))[
            "secrets.yaml"
        ].danger_ok
        assert registry_file.declared_totals["total"] == _SECRETS_CATALOGUED_TOTAL

    # frob:ticket T-0386
    def test_audit_reports_exhausted(self) -> None:
        """`audit_registry_file`'s one-line honest answer: zero
        unaccounted, zero malformed, over the REAL 3-entry file."""
        registry_file = load_registry_dir(_REGISTRY_DIR, ("secrets.yaml",))[
            "secrets.yaml"
        ].danger_ok
        audit = audit_registry_file(registry_file)

        assert audit.total == _SECRETS_CATALOGUED_TOTAL
        assert audit.exhausted is True
        assert audit.unaccounted == 0
        assert (
            audit.handled + audit.deferred + audit.duplicate + audit.out_of_scope
            == (_SECRETS_CATALOGUED_TOTAL)
        )

    # frob:ticket T-0386
    def test_every_deferred_entry_targets_an_open_ticket(self) -> None:
        """REG003's positive case, pinned to real data: every
        `deferred:T-XXXX` disposition in secrets.yaml names a ticket that
        actually exists and is not DONE -- a deferral to a closed or
        missing ticket is a silent drop wearing a disposition's clothes.
        secrets.yaml currently has no deferred entries, so this is
        vacuously satisfied but stays wired for the day one appears."""
        registry_file = load_registry_dir(_REGISTRY_DIR, ("secrets.yaml",))[
            "secrets.yaml"
        ].danger_ok
        queue = _real_queue()
        deferred = [
            entry
            for entries in registry_file.entry_lists.values()
            for entry in entries
            if entry.disposition.kind is DispositionKind.DEFERRED
        ]
        for entry in deferred:
            ticket_id = entry.disposition.target
            assert ticket_id is not None, f"{entry.id} deferred with no target ticket"
            ticket = queue.tickets.get(ticket_id)
            assert ticket is not None, f"{entry.id} defers to missing {ticket_id}"
            assert ticket.state.value != "done", (
                f"{entry.id} defers to closed ticket {ticket_id}"
            )


# frob:ticket T-0386
# frob:tests tests/test_registry_reconciliation_secrets.py::TestExhaustivenessGateOverRealSecrets.test_no_secrets_violations
class TestExhaustivenessGateOverRealSecrets:
    """`registry_gate` over the real registry dir raises zero violations
    for `secrets.yaml` specifically -- wired into `frob check` (the
    default gate run), not a side-channel-only assertion."""

    # frob:ticket T-0386
    def test_no_secrets_violations(self) -> None:
        real_queue = _real_queue()

        violations = registry_gate(
            _REPO_ROOT, real_queue, known_gate_rule_ids(), _REGISTRY_DIR
        )
        secrets_violations = [
            v for v in violations if v.file == "docs/design/registry/secrets.yaml"
        ]

        assert secrets_violations == []

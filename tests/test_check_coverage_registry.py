"""Tests for the T-0424 reflexive check-coverage registry
(docs/design/registry/check-coverage.yaml, docs/design/registry/
README.md#check-coverageyaml-t-0424-frobs-own-reflexive-check-coverage-registry).

Unlike `tests/test_registry_exhaustiveness.py` (synthetic fixtures), these
tests load the REAL `docs/design/registry/check-coverage.yaml` against the
REAL live `frob.gates.known_gate_rule_ids()` and the REAL ticket queue --
the whole point of this registry is that it is reflexive over this
build's actual state, not a fixture.
"""

from __future__ import annotations

from pathlib import Path

from frob.gates import known_gate_rule_ids
from frob.gates._registry_exhaustiveness import REGISTRY_FILES, registry_gate
from frob.registry import DispositionKind, audit_registry_file, load_registry_dir
from frob.tickets._models import TicketQueue

_REPO_ROOT = Path(__file__).resolve().parents[1]
_REGISTRY_DIR = _REPO_ROOT / "docs" / "design" / "registry"


class TestCheckCoverageRegistryFile:
    """`check-coverage.yaml` loads and is a real `RegistryFile` instance."""

    def test_is_in_registry_files(self) -> None:
        assert "check-coverage.yaml" in REGISTRY_FILES

    def test_loads_without_error(self) -> None:
        loaded = load_registry_dir(_REGISTRY_DIR, ("check-coverage.yaml",))

        assert "check-coverage.yaml" in loaded
        assert loaded["check-coverage.yaml"].is_ok

    def test_gate_rule_entries_match_live_known_rules(self) -> None:
        """Every `gate_rule_entries` id's `handled_by` target must be a
        rule id `known_gate_rule_ids()` reports LIVE right now -- this is
        the reflexive base case: an already-enforced concern's own
        existence-and-firing is what makes `handled_by:<self>` honest."""
        registry_file = load_registry_dir(_REGISTRY_DIR, ("check-coverage.yaml",))[
            "check-coverage.yaml"
        ].danger_ok
        known = known_gate_rule_ids()
        entries = registry_file.entry_lists["gate_rule_entries"]
        assert len(entries) == len(known)
        for entry in entries:
            assert entry.disposition.kind is DispositionKind.HANDLED_BY
            assert entry.disposition.target in known

    def test_concern_family_entries_are_deferred_or_handled(self) -> None:
        """Every audit concern row is either deferred to a live successor
        ticket or handled_by a real rule -- the exact progression the
        registry README documents (rows started all-deferred:T-0397 and
        move to handled_by as mechanisms land; the epic closed 2026-07-29
        with 7 handled / 6 deferred:T-1193)."""
        registry_file = load_registry_dir(_REGISTRY_DIR, ("check-coverage.yaml",))[
            "check-coverage.yaml"
        ].danger_ok
        entries = registry_file.entry_lists["concern_family_entries"]
        assert len(entries) >= 5
        for entry in entries:
            assert entry.disposition.kind in (
                DispositionKind.DEFERRED,
                DispositionKind.HANDLED_BY,
            ), entry
            if entry.disposition.kind is DispositionKind.DEFERRED:
                assert entry.disposition.target is not None, entry
                assert entry.disposition.target.startswith("T-"), entry

    def test_no_malformed_entries(self) -> None:
        registry_file = load_registry_dir(_REGISTRY_DIR, ("check-coverage.yaml",))[
            "check-coverage.yaml"
        ].danger_ok
        assert registry_file.malformed_count == 0

    def test_audit_reports_exhausted(self) -> None:
        registry_file = load_registry_dir(_REGISTRY_DIR, ("check-coverage.yaml",))[
            "check-coverage.yaml"
        ].danger_ok
        audit = audit_registry_file(registry_file)

        assert audit.exhausted is True
        assert audit.unaccounted == 0


class TestExhaustivenessGateOverRealCheckCoverage:
    """`registry_gate` over the real registry dir raises zero violations
    for `check-coverage.yaml` specifically -- the reflexive registry is
    itself fully dispositioned, not just loadable."""

    def test_no_check_coverage_violations(self) -> None:
        # A bare empty queue would make every `deferred:T-XXXX`
        # disposition in check-coverage.yaml classify as REG003 (ticket
        # does not exist), so this test loads the REAL queue instead.
        from frob.tickets import load_queue

        loaded_queue = load_queue(_REPO_ROOT)
        real_queue = (
            loaded_queue.danger_ok if loaded_queue.is_ok else TicketQueue(tickets={})
        )

        violations = registry_gate(
            _REPO_ROOT, real_queue, known_gate_rule_ids(), _REGISTRY_DIR
        )
        check_coverage_violations = [
            v
            for v in violations
            if v.file == "docs/design/registry/check-coverage.yaml"
        ]

        assert check_coverage_violations == []

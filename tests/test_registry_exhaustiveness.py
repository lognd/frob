"""Tests for frob.gates._registry_exhaustiveness -- REG001-REG005
(docs/modules/gates.md#registry-exhaustiveness-drift-lock-t-0343).

Fixtures are synthetic tempfile-backed `docs/design/registry/`-shaped
directories, never the real (1950-entry) registry -- same posture as
`tests/test_refs_gate.py`'s synthetic repos.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.gates._models import Severity
from frob.gates._registry_exhaustiveness import registry_gate
from frob.tickets._models import Origin, Ticket, TicketKind, TicketQueue, TicketState


def _queue(*tickets: Ticket) -> TicketQueue:
    return TicketQueue(tickets={t.id: t for t in tickets})


def _ticket(ticket_id: str, state: TicketState) -> Ticket:
    return Ticket(
        id=ticket_id,
        title="fixture ticket",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
    )


def _write_manifest(root: Path, filename: str, body: str) -> None:
    d = root / "docs" / "design" / "registry"
    d.mkdir(parents=True, exist_ok=True)
    (d / filename).write_text(body, encoding="utf-8")


def _rules(*rule_ids: str) -> list[str]:
    return list(rule_ids)


class TestDisposition:
    """REG001/REG002/REG003 -- the anti-lie mandate's core three checks."""

    def test_undispositioned_entry_fails(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    name: "Example"
    disposition: pending
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(tmp_path, _queue(), frozenset(), registry_dir)

        rules = _rules(*(v.rule for v in violations))
        assert "REG001" in rules

    def test_dangling_handled_by_fails(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    name: "Example"
    disposition: "handled_by:NOTAREALRULE999"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(
            tmp_path, _queue(), frozenset({"REF001"}), registry_dir
        )

        rules = _rules(*(v.rule for v in violations))
        assert "REG002" in rules

    def test_handled_by_real_rule_passes(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    name: "Example"
    disposition: "handled_by:REF001"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(
            tmp_path, _queue(), frozenset({"REF001"}), registry_dir
        )

        assert violations == ()

    def test_deferred_to_closed_ticket_fails(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    name: "Example"
    disposition: "deferred:T-0001"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"
        queue = _queue(_ticket("T-0001", TicketState.DONE))

        violations = registry_gate(tmp_path, queue, frozenset(), registry_dir)

        rules = _rules(*(v.rule for v in violations))
        assert "REG003" in rules

    def test_deferred_to_missing_ticket_fails(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    name: "Example"
    disposition: "deferred:T-9999"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(tmp_path, _queue(), frozenset(), registry_dir)

        rules = _rules(*(v.rule for v in violations))
        assert "REG003" in rules

    def test_deferred_to_open_ticket_passes(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    name: "Example"
    disposition: "deferred:T-0001"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"
        queue = _queue(_ticket("T-0001", TicketState.QUEUED))

        violations = registry_gate(tmp_path, queue, frozenset(), registry_dir)

        assert violations == ()

    def test_fully_dispositioned_fixture_passes(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
total: 4
entries:
  - id: "PAT-HANDLED"
    disposition: "handled_by:REF001"
    cross_refs: []
  - id: "PAT-DEFERRED"
    disposition: "deferred:T-0001"
    cross_refs: []
  - id: "PAT-DUP"
    disposition: "duplicate_of:PAT-HANDLED"
    cross_refs: []
  - id: "PAT-OOS"
    disposition: "out_of_scope:no code executes this concept"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"
        queue = _queue(_ticket("T-0001", TicketState.QUEUED))

        violations = registry_gate(tmp_path, queue, frozenset({"REF001"}), registry_dir)

        assert violations == ()

    def test_bare_addressed_fails(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    disposition: addressed
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(tmp_path, _queue(), frozenset(), registry_dir)

        rules = _rules(*(v.rule for v in violations))
        assert "REG001" in rules

    def test_dangling_duplicate_of_fails(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    disposition: "duplicate_of:PAT-NONEXISTENT"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(tmp_path, _queue(), frozenset(), registry_dir)

        rules = _rules(*(v.rule for v in violations))
        assert "REG004" in rules

    def test_out_of_scope_no_reason_fails(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    disposition: "out_of_scope:"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(tmp_path, _queue(), frozenset(), registry_dir)

        rules = _rules(*(v.rule for v in violations))
        assert "REG001" in rules

    def test_severity_is_error(self, tmp_path: Path) -> None:
        # T-0426: REG fires at ERROR now that the registry backlog is fully
        # drained to zero. An undispositioned entry is a hard failure, not a
        # warning -- a registry entry read by no enforcing rule and carrying
        # no honest disposition is exactly the catalogued-not-enforced lie the
        # gate exists to catch.
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    disposition: pending
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(tmp_path, _queue(), frozenset(), registry_dir)

        assert all(v.severity == Severity.ERROR for v in violations)


class TestTotalDrift:
    """REG005 -- declared `total:`/`<prefix>_total:` drift from actual entries."""

    def test_total_mismatch_fails(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
total: 5
entries:
  - id: "PAT-EXAMPLE"
    disposition: "handled_by:REF001"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(
            tmp_path, _queue(), frozenset({"REF001"}), registry_dir
        )

        rules = _rules(*(v.rule for v in violations))
        assert "REG005" in rules

    def test_split_entries_key_total_checked(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "weaknesses.yaml",
            """\
schema_version: 1
cwe_total: 2
cwe_entries:
  - id: "CWE-1"
    disposition: "handled_by:REF001"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(
            tmp_path, _queue(), frozenset({"REF001"}), registry_dir
        )

        rules = _rules(*(v.rule for v in violations))
        assert "REG005" in rules

    def test_no_declared_total_not_checked(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    disposition: "handled_by:REF001"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(
            tmp_path, _queue(), frozenset({"REF001"}), registry_dir
        )

        assert violations == ()


class TestSplitReconciliation:
    """REG004 -- RECONCILIATION.md-documented split entries still unlinked."""

    def test_documented_split_with_empty_cross_refs_fails(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-CIRCUIT-BREAKER"
    disposition: "handled_by:REF001"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"
        (registry_dir / "RECONCILIATION.md").write_text(
            """\
### (b) SPLIT entries -- same real-world item, unlinked ids across files

| Concept | Appears in | Registry ids (unlinked) |
|---|---|---|
| Circuit Breaker | catalog, patterns | `PAT-CIRCUIT-BREAKER` |

### (c) Entries with no DISPOSITION yet
""",
            encoding="utf-8",
        )

        violations = registry_gate(
            tmp_path, _queue(), frozenset({"REF001"}), registry_dir
        )

        rules = _rules(*(v.rule for v in violations))
        assert "REG004" in rules

    def test_documented_split_with_cross_refs_passes(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-CIRCUIT-BREAKER"
    disposition: "handled_by:REF001"
    cross_refs: ["ACC-5-2-CIRCUIT-BREAKER"]
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"
        (registry_dir / "RECONCILIATION.md").write_text(
            """\
### (b) SPLIT entries -- same real-world item, unlinked ids across files

| Concept | Appears in | Registry ids (unlinked) |
|---|---|---|
| Circuit Breaker | catalog, patterns | `PAT-CIRCUIT-BREAKER` |

### (c) Entries with no DISPOSITION yet
""",
            encoding="utf-8",
        )

        violations = registry_gate(
            tmp_path, _queue(), frozenset({"REF001"}), registry_dir
        )

        assert violations == ()


class TestMissingDir:
    """No `docs/design/registry/` at all is a clean no-op, not a crash."""

    def test_missing_registry_dir_returns_empty(self, tmp_path: Path) -> None:
        violations = registry_gate(
            tmp_path, _queue(), frozenset(), tmp_path / "does" / "not" / "exist"
        )

        assert violations == ()

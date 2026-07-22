# frob:waive SCOPE001 reason="T-0407's declared scope is src/frob/+docs/design/registry/; tests/** is leased in-progress by T-0160 so the scope cannot be formally extended here, same ad-hoc precedent as config.py's existing T-0458/T-0455 SCOPE001 waives -- this file's edits are new pytest coverage for T-0407's own gate refactor"  # noqa: E501
"""Tests for frob.gates._registry_exhaustiveness -- REG001-REG007
(docs/modules/gates.md#registry-exhaustiveness-drift-lock-t-0343, REG006/
REG007 added by T-0407).

Fixtures are synthetic tempfile-backed `docs/design/registry/`-shaped
directories, never the real (1950-entry) registry -- same posture as
`tests/test_refs_gate.py`'s synthetic repos.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.gates._models import Severity
from frob.gates._registry_exhaustiveness import registry_gate
from frob.graph._models import Edge, EdgeKind, GraphSnapshot
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


class TestMalformedEntry:
    """REG006 (T-0407) -- a structurally malformed list item is loud, not
    silently dropped from the count."""

    def test_malformed_entry_fails(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    disposition: "handled_by:REF001"
    cross_refs: []
  - "not a mapping at all"
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(
            tmp_path, _queue(), frozenset({"REF001"}), registry_dir
        )

        rules = _rules(*(v.rule for v in violations))
        assert "REG006" in rules

    def test_entry_missing_id_fails(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - name: "no id field"
    disposition: "handled_by:REF001"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(
            tmp_path, _queue(), frozenset({"REF001"}), registry_dir
        )

        rules = _rules(*(v.rule for v in violations))
        assert "REG006" in rules

    def test_all_well_formed_entries_no_reg006(self, tmp_path: Path) -> None:
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

        rules = _rules(*(v.rule for v in violations))
        assert "REG006" not in rules


class TestDuplicateId:
    """REG007 (T-0407) -- the same id defined by two or more entries is a
    real collision, distinct from an intentional `duplicate_of:` link."""

    def test_duplicate_id_across_files_fails(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-SHARED"
    disposition: "handled_by:REF001"
    cross_refs: []
""",
        )
        _write_manifest(
            tmp_path,
            "arch-checks.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-SHARED"
    disposition: "handled_by:REF001"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(
            tmp_path, _queue(), frozenset({"REF001"}), registry_dir
        )

        rules = _rules(*(v.rule for v in violations))
        assert "REG007" in rules

    def test_duplicate_id_same_file_fails(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-SHARED"
    disposition: "handled_by:REF001"
    cross_refs: []
  - id: "PAT-SHARED"
    disposition: "handled_by:REF001"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(
            tmp_path, _queue(), frozenset({"REF001"}), registry_dir
        )

        rules = _rules(*(v.rule for v in violations))
        assert "REG007" in rules

    def test_no_duplicate_ids_no_reg007(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-ONE"
    disposition: "handled_by:REF001"
    cross_refs: []
  - id: "PAT-TWO"
    disposition: "duplicate_of:PAT-ONE"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(
            tmp_path, _queue(), frozenset({"REF001"}), registry_dir
        )

        rules = _rules(*(v.rule for v in violations))
        assert "REG007" not in rules


# frob:ticket T-0428
def _snapshot(*edges: Edge) -> GraphSnapshot:
    """Minimal `GraphSnapshot` carrying only the edges REG008/REG009 need
    (no real symbol table required for a pure-edge-index cross-check)."""
    return GraphSnapshot(root=".", symbols={}, edges=edges)


# frob:ticket T-0428
class TestEnforcesConformance:
    """T-0428: REG008/REG009, the derived-coverage two-SSOT (code
    `frob:enforces` <-> yaml `handled_by`) bidirectional conformance
    check."""

    # frob:tests tests/test_registry_exhaustiveness.py::TestEnforcesConformance.test_handled_by_with_no_frob_enforces_edge_warns  # noqa: E501
    # frob:ticket T-0428
    def test_handled_by_with_no_frob_enforces_edge_warns(self, tmp_path: Path) -> None:
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
            tmp_path,
            _queue(),
            frozenset({"REF001"}),
            registry_dir,
            snapshot=_snapshot(),
        )

        rules = _rules(*(v.rule for v in violations))
        assert "REG008" in rules
        reg008 = next(v for v in violations if v.rule == "REG008")
        assert reg008.severity == Severity.WARN

    # frob:ticket T-0428
    def test_handled_by_with_frob_enforces_edge_is_silent(self, tmp_path: Path) -> None:
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
        snapshot = _snapshot(
            Edge(
                src="src/frob/gates/_refs.py::ref001_gate",
                kind=EdgeKind.ENFORCES,
                target="PAT-EXAMPLE",
                origin="src/frob/gates/_refs.py:1",
            )
        )

        violations = registry_gate(
            tmp_path, _queue(), frozenset({"REF001"}), registry_dir, snapshot=snapshot
        )

        rules = _rules(*(v.rule for v in violations))
        assert "REG008" not in rules

    # frob:ticket T-0428
    def test_no_snapshot_skips_reg008_reg009(self, tmp_path: Path) -> None:
        """T-0428: `snapshot=None` (the default) makes no claim about
        code-side enforcement -- REG008/REG009 simply do not run, rather
        than failing every existing handled_by entry closed by
        assumption."""
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

        rules = _rules(*(v.rule for v in violations))
        assert "REG008" not in rules
        assert "REG009" not in rules

    # frob:ticket T-0428
    def test_phantom_enforces_edge_warns(self, tmp_path: Path) -> None:
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
        snapshot = _snapshot(
            Edge(
                src="src/frob/gates/_refs.py::ref001_gate",
                kind=EdgeKind.ENFORCES,
                target="NOT-A-REAL-CONCEPT-ID",
                origin="src/frob/gates/_refs.py:1",
            ),
            Edge(
                src="src/frob/gates/_refs.py::ref001_gate",
                kind=EdgeKind.ENFORCES,
                target="PAT-EXAMPLE",
                origin="src/frob/gates/_refs.py:1",
            ),
        )

        violations = registry_gate(
            tmp_path, _queue(), frozenset({"REF001"}), registry_dir, snapshot=snapshot
        )

        rules = _rules(*(v.rule for v in violations))
        assert "REG009" in rules
        reg009 = next(v for v in violations if v.rule == "REG009")
        assert reg009.severity == Severity.WARN

    # frob:ticket T-0428
    def test_matching_enforces_edge_no_reg009(self, tmp_path: Path) -> None:
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
        snapshot = _snapshot(
            Edge(
                src="src/frob/gates/_refs.py::ref001_gate",
                kind=EdgeKind.ENFORCES,
                target="PAT-EXAMPLE",
                origin="src/frob/gates/_refs.py:1",
            )
        )

        violations = registry_gate(
            tmp_path, _queue(), frozenset({"REF001"}), registry_dir, snapshot=snapshot
        )

        rules = _rules(*(v.rule for v in violations))
        assert "REG009" not in rules

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
    disposition: "out_of_scope:none -- no code executes this concept"
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


class TestOutOfScopeCaughtBy:
    """REG011 (T-0680) -- routes registry-YAML `out_of_scope:<reason>`
    strings through the same T-0382 `caught_by` token-resolution
    verification `strata._threat`/`strata._compliance` already run for
    their own model objects."""

    def test_reason_naming_no_control_warns(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    disposition: "out_of_scope:advisory-design-pattern-recommendation"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(tmp_path, _queue(), frozenset(), registry_dir)

        rules = _rules(*(v.rule for v in violations))
        assert "REG011" in rules
        reg011 = next(v for v in violations if v.rule == "REG011")
        assert reg011.severity == Severity.WARN

    def test_reason_naming_unresolved_rule_warns(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    disposition: "out_of_scope:caught by SEC999 elsewhere"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        # SEC999 is not in the (empty) known-rules set passed here, so the
        # named control does not resolve -- a fabricated/typo'd reference.
        violations = registry_gate(tmp_path, _queue(), frozenset(), registry_dir)

        rules = _rules(*(v.rule for v in violations))
        assert "REG011" in rules

    def test_reason_naming_resolved_rule_is_silent(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    disposition: "out_of_scope:caught by SEC999 elsewhere"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        # SEC999 IS in known_rules here -- the named control resolves.
        violations = registry_gate(
            tmp_path, _queue(), frozenset({"SEC999"}), registry_dir
        )

        rules = _rules(*(v.rule for v in violations))
        assert "REG011" not in rules

    def test_substantive_reasoned_none_is_silent(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    disposition: "out_of_scope:none -- no code executes this concept"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(tmp_path, _queue(), frozenset(), registry_dir)

        rules = _rules(*(v.rule for v in violations))
        assert "REG011" not in rules

    def test_bare_none_is_not_substantive(self, tmp_path: Path) -> None:
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    disposition: "out_of_scope:none"
    cross_refs: []
""",
        )
        registry_dir = tmp_path / "docs" / "design" / "registry"

        violations = registry_gate(tmp_path, _queue(), frozenset(), registry_dir)

        rules = _rules(*(v.rule for v in violations))
        assert "REG011" in rules


# frob:ticket T-0894
def _git_init(root: Path) -> None:
    """Minimal git repo bootstrap for path_ever_tracked's history checks
    (mirrors tests/test_gates.py's own `_git_init` helper -- this module
    has no such fixture yet, so it is duplicated at file scope rather than
    importing across test modules)."""
    import subprocess

    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / ".gitkeep").write_text("")
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=root, check=True)


# frob:ticket T-0894
class TestPathEverTracked:
    """`frob.gates._registry_exhaustiveness.path_ever_tracked` -- the
    shared "was this ever committed on HEAD's history" signal T-0894
    built so registry-backed gates can distinguish never-adopted from
    adopted-then-deleted."""

    def test_never_committed_path_is_false(self, tmp_path: Path) -> None:
        """A path with no commit history at all is False -- the ordinary
        never-adopted case."""
        from frob.gates._registry_exhaustiveness import path_ever_tracked

        _git_init(tmp_path)
        assert path_ever_tracked(tmp_path, "docs/design/registry") is False

    def test_deleted_after_commit_is_true(self, tmp_path: Path) -> None:
        """A path committed once and then deleted from the working tree
        is True -- the adopted-then-deleted case this ticket exists for."""
        import subprocess

        from frob.gates._registry_exhaustiveness import path_ever_tracked

        _git_init(tmp_path)
        target_dir = tmp_path / "docs" / "design" / "registry"
        target_dir.mkdir(parents=True)
        (target_dir / "compliance.yaml").write_text("entries: []\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "adopt registry"], cwd=tmp_path, check=True
        )
        (target_dir / "compliance.yaml").unlink()
        target_dir.rmdir()

        assert path_ever_tracked(tmp_path, "docs/design/registry") is True

    def test_git_failure_is_false(self, tmp_path: Path) -> None:
        """A directory that is not a git repo at all degrades to False
        (the existing "never adopted" posture), not a crash or a false
        violation from a plumbing failure."""
        from frob.gates._registry_exhaustiveness import path_ever_tracked

        assert path_ever_tracked(tmp_path, "docs/design/registry") is False


# frob:ticket T-0894
class TestDeletedRegistry:
    """REG012 (T-0894) -- `registry_gate` distinguishes a `docs/design/
    registry/` dir that never existed from one that was committed and
    then deleted."""

    def test_never_adopted_registry_dir_is_silent(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        violations = registry_gate(
            tmp_path, _queue(), frozenset(), tmp_path / "docs" / "design" / "registry"
        )
        assert not any(v.rule == "REG012" for v in violations)

    def test_deleted_after_adoption_fires_reg012(self, tmp_path: Path) -> None:
        import subprocess

        registry_dir = tmp_path / "docs" / "design" / "registry"
        _git_init(tmp_path)
        _write_manifest(
            tmp_path,
            "patterns.yaml",
            """\
schema_version: 1
entries:
  - id: "PAT-EXAMPLE"
    disposition: "handled_by:SEC003"
""",
        )
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "adopt registry"], cwd=tmp_path, check=True
        )
        (registry_dir / "patterns.yaml").unlink()
        registry_dir.rmdir()

        violations = registry_gate(tmp_path, _queue(), frozenset(), registry_dir)

        rules = _rules(*(v.rule for v in violations))
        assert "REG012" in rules
        reg012 = next(v for v in violations if v.rule == "REG012")
        assert reg012.severity == Severity.ERROR


# frob:ticket T-1020
class TestArchChecksReg008BurnDown:
    """T-1020: REG008 burn-down over `docs/design/registry/arch-checks.yaml`
    -- the real "does the recorded handled_by claim actually verify against
    live code" smoke test (T-0813/T-0820 precedent), same shape as
    `TestComplianceGate.test_compliance005_real_repo_registry_passes` --
    runs `registry_gate` over this repo's OWN live registry + graph, not a
    synthetic fixture."""

    # frob:tests tests/test_registry_exhaustiveness.py::TestArchChecksReg008BurnDown.test_no_reg008_findings_for_arch_checks_yaml  # noqa: E501
    def test_no_reg008_findings_for_arch_checks_yaml(self) -> None:
        """Every `docs/design/registry/arch-checks.yaml` entry dispositioned
        `handled_by:<RULE>` must carry a real `frob:enforces <ENTRY-ID>`
        edge somewhere in code -- the acceptance criterion this ticket's
        Done report claims."""
        from frob.gates import _KNOWN_GATE_RULES
        from frob.graph import build_graph

        root = Path(__file__).resolve().parents[1]
        snapshot = build_graph(root, root / ".frob" / "cache.db").danger_ok

        violations = registry_gate(
            root,
            _queue(),
            _KNOWN_GATE_RULES,
            snapshot=snapshot,
        )

        reg008_arch_checks = [
            v for v in violations if v.rule == "REG008" and "arch-checks.yaml" in v.file
        ]
        assert reg008_arch_checks == []


# frob:ticket T-1020
class TestSystemDesignReg008BurnDown:
    """T-1020 follow-up: REG008 burn-down over `docs/design/registry/
    system-design.yaml`'s SDC-13 remainder (T-0960/T-0962's REL39x
    process-bounds/supply-chain-boot obligation entrypoints) -- same real
    "does the recorded handled_by claim actually verify against live
    code" smoke test shape as `TestArchChecksReg008BurnDown`."""

    # frob:tests tests/test_registry_exhaustiveness.py::TestSystemDesignReg008BurnDown.test_no_reg008_findings_for_system_design_yaml  # noqa: E501
    def test_no_reg008_findings_for_system_design_yaml(self) -> None:
        """Every `docs/design/registry/system-design.yaml` entry
        dispositioned `handled_by:<RULE>` must carry a real `frob:enforces
        <ENTRY-ID>` edge somewhere in code."""
        from frob.gates import _KNOWN_GATE_RULES
        from frob.graph import build_graph

        root = Path(__file__).resolve().parents[1]
        snapshot = build_graph(root, root / ".frob" / "cache.db").danger_ok

        violations = registry_gate(
            root,
            _queue(),
            _KNOWN_GATE_RULES,
            snapshot=snapshot,
        )

        reg008_system_design = [
            v
            for v in violations
            if v.rule == "REG008" and "system-design.yaml" in v.file
        ]
        assert reg008_system_design == []


# frob:ticket T-1020
class TestCheckCoverageReg008BurnDown:
    """T-1020 follow-up: REG008 burn-down over `docs/design/registry/
    check-coverage.yaml` -- one `CHK-GATE-<RULE>` entry per known gate
    rule id (the coverage denominator), each needing a real
    `frob:enforces CHK-GATE-<RULE>` edge at the site that actually
    constructs that rule's `Violation`. Same real "does the recorded
    handled_by claim actually verify against live code" smoke test shape
    as `TestArchChecksReg008BurnDown`/`TestSystemDesignReg008BurnDown`."""

    # frob:tests tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown.test_no_reg008_findings_for_check_coverage_yaml  # noqa: E501
    def test_no_reg008_findings_for_check_coverage_yaml(self) -> None:
        """Every `docs/design/registry/check-coverage.yaml` entry
        dispositioned `handled_by:<RULE>` must carry a real `frob:enforces
        CHK-GATE-<RULE>` edge somewhere in code."""
        from frob.gates import _KNOWN_GATE_RULES
        from frob.graph import build_graph

        root = Path(__file__).resolve().parents[1]
        snapshot = build_graph(root, root / ".frob" / "cache.db").danger_ok

        violations = registry_gate(
            root,
            _queue(),
            _KNOWN_GATE_RULES,
            snapshot=snapshot,
        )

        reg008_check_coverage = [
            v
            for v in violations
            if v.rule == "REG008" and "check-coverage.yaml" in v.file
        ]
        assert reg008_check_coverage == []


# frob:ticket T-1020
class TestComplianceReg008BurnDown:
    """T-1020 follow-up: REG008 burn-down over `docs/design/registry/
    compliance.yaml`'s 17 `CMPL_REGISTRY_UNIT_IDS` checkable-control units
    (T-0833 flipped them to `handled_by:COMPLIANCE005`) -- same real "does
    the recorded handled_by claim actually verify against live code"
    smoke test shape as `TestArchChecksReg008BurnDown` and siblings.
    Landed LAST per dispatch coordination: T-1019 concurrently rewrote
    REG011 disposition reasons in this same file (a different YAML key,
    `out_of_scope:<reason>` vs this ticket's `handled_by`/`frob:enforces`
    edges) -- re-merged main immediately before this batch."""

    # frob:tests tests/test_registry_exhaustiveness.py::TestComplianceReg008BurnDown.test_no_reg008_findings_for_compliance_yaml  # noqa: E501
    def test_no_reg008_findings_for_compliance_yaml(self) -> None:
        """Every `docs/design/registry/compliance.yaml` entry dispositioned
        `handled_by:<RULE>` must carry a real `frob:enforces <ENTRY-ID>`
        edge somewhere in code."""
        from frob.gates import _KNOWN_GATE_RULES
        from frob.graph import build_graph

        root = Path(__file__).resolve().parents[1]
        snapshot = build_graph(root, root / ".frob" / "cache.db").danger_ok

        violations = registry_gate(
            root,
            _queue(),
            _KNOWN_GATE_RULES,
            snapshot=snapshot,
        )

        reg008_compliance = [
            v for v in violations if v.rule == "REG008" and "compliance.yaml" in v.file
        ]
        assert reg008_compliance == []

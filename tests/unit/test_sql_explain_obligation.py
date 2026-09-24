"""SQLEXPLAIN001 gate coverage (T-5339): `frob.gates._sql_explain_
obligation.sql_explain_obligation_gate` over a hand-built `GraphSnapshot`
(same posture `tests/unit/test_design_invariants.py`'s INV007/INV008
tests use -- the gate is pure over its inputs, no full `frob check` run
needed), plus a positive control over the real
`tests/fixtures/sql/explain/**` fixture pair.

frob:ticket T-5339
"""

from __future__ import annotations

from pathlib import Path

from frob.gates._sql_explain_obligation import sql_explain_obligation_gate
from frob.graph import Edge, EdgeKind, GraphSnapshot

_FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "sql" / "explain"


def _snapshot(root: Path, edges: tuple[Edge, ...]) -> GraphSnapshot:
    """A minimal `GraphSnapshot` carrying only `edges` -- the gate under
    test reads nothing else off the snapshot."""
    return GraphSnapshot(root=str(root), symbols={}, edges=edges)


def _waive_edge(*, target: str, origin: str, explain: str | None = None) -> Edge:
    """One `frob:waive <target> reason="..."` edge, optionally carrying an
    `explain="..."` attribute -- the shape `frob.graph.dsl` would parse a
    real `# frob:waive Frob_L002 reason="..." explain="..."` comment
    into."""
    attrs = {"reason": "test waiver"}
    if explain is not None:
        attrs["explain"] = explain
    return Edge(
        src=origin.split(":", 1)[0],
        kind=EdgeKind.WAIVE,
        target=target,
        origin=origin,
        attrs=attrs,
    )


# frob:tests src/frob/gates/_sql_explain_obligation.py::sql_explain_obligation_gate kind="unit"  # noqa: E501
def test_bare_waiver_with_no_explain_attr_fires(tmp_path: Path) -> None:
    """Positive control: a `frob:waive Frob_L002 reason="..."` with no
    `explain=` attribute at all is unproven -- SQLEXPLAIN001 fires."""
    edge = _waive_edge(target="Frob_L002", origin="query.py:3")
    violations = sql_explain_obligation_gate(tmp_path, _snapshot(tmp_path, (edge,)))
    assert len(violations) == 1
    assert violations[0].rule == "SQLEXPLAIN001"
    assert violations[0].file == "query.py"
    assert violations[0].line == 3


# frob:tests src/frob/gates/_sql_explain_obligation.py::sql_explain_obligation_gate kind="unit"  # noqa: E501
def test_explain_attr_naming_a_missing_file_still_fires(tmp_path: Path) -> None:
    """An `explain="..."` attribute naming a file that does not exist on
    disk is exactly as unproven as no attribute at all."""
    edge = _waive_edge(
        target="Frob_L002",
        origin="query.py:3",
        explain="tests/fixtures/sql/explain/does_not_exist.explain.txt",
    )
    violations = sql_explain_obligation_gate(tmp_path, _snapshot(tmp_path, (edge,)))
    assert len(violations) == 1
    assert violations[0].rule == "SQLEXPLAIN001"


# frob:tests src/frob/gates/_sql_explain_obligation.py::sql_explain_obligation_gate kind="unit"  # noqa: E501
def test_explain_attr_outside_the_artifact_dir_still_fires(tmp_path: Path) -> None:
    """An `explain="..."` attribute naming a REAL file that lives outside
    `EXPLAIN_ARTIFACT_DIR` is not accepted as proof (a claim this gate
    cannot itself audit is not a discharged obligation)."""
    outside = tmp_path / "elsewhere.txt"
    outside.write_text("not a real artifact directory\n", encoding="utf-8")
    edge = _waive_edge(target="Frob_L002", origin="query.py:3", explain="elsewhere.txt")
    violations = sql_explain_obligation_gate(tmp_path, _snapshot(tmp_path, (edge,)))
    assert len(violations) == 1


# frob:tests src/frob/gates/_sql_explain_obligation.py::sql_explain_obligation_gate kind="unit"  # noqa: E501
def test_explain_attr_naming_a_real_artifact_is_clean(tmp_path: Path) -> None:
    """A real, existing artifact under `EXPLAIN_ARTIFACT_DIR` discharges
    the obligation -- no finding."""
    artifact_dir = tmp_path / "tests" / "fixtures" / "sql" / "explain"
    artifact_dir.mkdir(parents=True)
    artifact = artifact_dir / "proof.explain.txt"
    artifact.write_text("QUERY PLAN\nSeq Scan on sessions\n", encoding="utf-8")
    edge = _waive_edge(
        target="Frob_L002",
        origin="query.py:3",
        explain="tests/fixtures/sql/explain/proof.explain.txt",
    )
    assert sql_explain_obligation_gate(tmp_path, _snapshot(tmp_path, (edge,))) == ()


# frob:tests src/frob/gates/_sql_explain_obligation.py::sql_explain_obligation_gate kind="unit"  # noqa: E501
def test_non_obligated_rule_is_never_flagged(tmp_path: Path) -> None:
    """A `frob:waive` on a rule outside the discovered obligation
    prefixes (e.g. a plain `RUFF001`) is never this gate's business, with
    or without an `explain=` attribute."""
    edge = _waive_edge(target="RUFF001", origin="query.py:3")
    assert sql_explain_obligation_gate(tmp_path, _snapshot(tmp_path, (edge,))) == ()


# frob:tests src/frob/gates/_sql_explain_obligation.py::sql_explain_obligation_gate kind="unit"  # noqa: E501
def test_non_waive_edge_is_ignored(tmp_path: Path) -> None:
    """A non-WAIVE edge targeting a `Frob_L`-prefixed name (e.g. a
    `frob:tests` edge, which would never actually name a rule id, but
    proves the `edge.kind` filter) is never this gate's business."""
    edge = Edge(
        src="query.py",
        kind=EdgeKind.TESTS,
        target="Frob_L002",
        origin="query.py:3",
        attrs={"kind": "unit"},
    )
    assert sql_explain_obligation_gate(tmp_path, _snapshot(tmp_path, (edge,))) == ()


# frob:tests tests/fixtures/sql/explain/unproven_waiver.py
# frob:tests tests/fixtures/sql/explain/proven_waiver.py
# frob:tests src/frob/gates/_sql_explain_obligation.py::sql_explain_obligation_gate kind="unit"  # noqa: E501
def test_real_fixture_pair_unproven_fires_proven_is_clean() -> None:
    """Real fixture positive control (T-5339's own acceptance criterion:
    'a waiver attempt with and without the attached EXPLAIN artifact'):
    `unproven_waiver.py`'s bare-prose waiver fires; `proven_waiver.py`'s
    waiver, naming the real `delete_all_sessions.explain.txt` artifact
    that ships alongside it, does not."""
    repo_root = Path(__file__).resolve().parents[2]
    unproven_edge = _waive_edge(
        target="Frob_L002",
        origin="tests/fixtures/sql/explain/unproven_waiver.py:3",
    )
    proven_edge = _waive_edge(
        target="Frob_L002",
        origin="tests/fixtures/sql/explain/proven_waiver.py:3",
        explain="tests/fixtures/sql/explain/delete_all_sessions.explain.txt",
    )
    unproven = sql_explain_obligation_gate(
        repo_root, _snapshot(repo_root, (unproven_edge,))
    )
    proven = sql_explain_obligation_gate(
        repo_root, _snapshot(repo_root, (proven_edge,))
    )
    assert len(unproven) == 1
    assert unproven[0].rule == "SQLEXPLAIN001"
    assert proven == ()


# frob:tests src/frob/gates/_sql_explain_obligation.py::_discover_obligation_rule_prefixes kind="unit"  # noqa: E501
def test_discover_obligation_rule_prefixes_includes_default() -> None:
    """`_discover_obligation_rule_prefixes` always includes the default
    `Frob_L` prefix, even with no `frob.sql` submodule opting in yet."""
    from frob.gates._sql_explain_obligation import _discover_obligation_rule_prefixes

    assert "Frob_L" in _discover_obligation_rule_prefixes()

"""frob.sql._orm_rules coverage (T-5337): one positive + one negative
control per SQL10x rule, plus `migration_scan`.

frob:ticket T-5337
"""

from __future__ import annotations

from pathlib import Path

from frob.sql._orm_rules import migration_scan, orm_rule_findings

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "sql"


# frob:tests src/frob/sql/_orm_rules.py::orm_rule_findings kind="unit"
# frob:tests src/frob/sql/_orm_rules.py::OrmRuleFinding kind="unit"  # noqa: E501
def test_sql101_lazy_relationship_in_loop_flagged() -> None:
    """A lazy-relationship attribute access inside a loop with no eager
    load anywhere in the function is SQL101."""
    findings = orm_rule_findings(_FIXTURE_ROOT / "orm")
    matching = [
        f
        for f in findings
        if f.rule == "SQL101" and f.file.endswith("n_plus_one_loop.py")
    ]
    assert len(matching) == 1, findings


# frob:tests src/frob/sql/_orm_rules.py::orm_rule_findings kind="unit"
def test_sql101_eager_loaded_loop_not_flagged() -> None:
    """The same loop shape, eager-loaded via joinedload, is not SQL101."""
    findings = orm_rule_findings(_FIXTURE_ROOT / "orm")
    matching = [
        f
        for f in findings
        if f.rule == "SQL101" and f.file.endswith("eager_loaded_loop.py")
    ]
    assert matching == []


# frob:tests src/frob/sql/_orm_rules.py::orm_rule_findings kind="unit"
def test_sql102_unbounded_all_flagged() -> None:
    """A bare `.all()` call with no `.limit(...)` in the chain is
    SQL102."""
    findings = orm_rule_findings(_FIXTURE_ROOT / "orm")
    matching = [
        f
        for f in findings
        if f.rule == "SQL102" and f.file.endswith("unbounded_all.py")
    ]
    assert len(matching) == 1, findings


# frob:tests src/frob/sql/_orm_rules.py::orm_rule_findings kind="unit"
def test_sql102_limited_all_not_flagged() -> None:
    """`.limit(...).all()` in the same chain is not SQL102."""
    findings = orm_rule_findings(_FIXTURE_ROOT / "orm")
    matching = [
        f
        for f in findings
        if f.rule == "SQL102" and f.file.endswith("eager_loaded_loop.py")
    ]
    assert matching == []


# frob:tests src/frob/sql/_orm_rules.py::orm_rule_findings kind="unit"
def test_sql105_multi_write_no_transaction_flagged() -> None:
    """Two write calls in one function with no atomic/transaction/begin
    wrapper is SQL105."""
    findings = orm_rule_findings(_FIXTURE_ROOT / "orm")
    matching = [
        f
        for f in findings
        if f.rule == "SQL105" and f.file.endswith("multi_write_no_transaction.py")
    ]
    assert len(matching) == 1, findings


# frob:tests src/frob/sql/_orm_rules.py::orm_rule_findings kind="unit"
def test_sql105_wrapped_transaction_not_flagged() -> None:
    """The same two-write shape inside `atomic()` is not SQL105."""
    findings = orm_rule_findings(_FIXTURE_ROOT / "orm")
    matching = [
        f
        for f in findings
        if f.rule == "SQL105" and f.file.endswith("wrapped_transaction.py")
    ]
    assert matching == []


# frob:tests src/frob/sql/_orm_rules.py::migration_scan kind="unit"
# frob:tests src/frob/sql/_orm_rules.py::MigrationIndexInfo kind="unit"  # noqa: E501
def test_migration_scan_parses_create_index() -> None:
    """`migration_scan` parses a `CREATE INDEX ... ON table (cols)`
    statement into table + column names."""
    infos = migration_scan(_FIXTURE_ROOT / "migrations_indexed")
    assert len(infos) == 1, infos
    assert infos[0].table == "orders"
    assert infos[0].columns == ("customer_id",)


# frob:tests src/frob/sql/_orm_rules.py::orm_rule_findings kind="unit"
def test_sql104_missing_index_flagged() -> None:
    """A ForeignKey column with no matching migration index is
    SQL104."""
    findings = orm_rule_findings(_FIXTURE_ROOT / "migrations_missing")
    matching = [f for f in findings if f.rule == "SQL104"]
    assert len(matching) == 1, findings
    assert matching[0].file.endswith("models.py")


# frob:tests src/frob/sql/_orm_rules.py::orm_rule_findings kind="unit"
def test_sql104_indexed_column_not_flagged() -> None:
    """The same FK column shape, with a matching migration index, is not
    SQL104."""
    findings = orm_rule_findings(_FIXTURE_ROOT / "migrations_indexed")
    matching = [f for f in findings if f.rule == "SQL104"]
    assert matching == []


# frob:tests src/frob/sql/_orm_rules.py::orm_rule_findings kind="unit"
def test_sql106_missing_pool_config_flagged() -> None:
    """Real SQL surface with no pool-config token anywhere is SQL106,
    one repo-level finding (`file=""`)."""
    findings = orm_rule_findings(_FIXTURE_ROOT / "pool_missing")
    matching = [f for f in findings if f.rule == "SQL106"]
    assert len(matching) == 1, findings
    assert matching[0].file == ""


# frob:tests src/frob/sql/_orm_rules.py::orm_rule_findings kind="unit"
def test_sql106_configured_pool_not_flagged() -> None:
    """The same SQL surface, with a `pool_size` config token present, is
    not SQL106."""
    findings = orm_rule_findings(_FIXTURE_ROOT / "pool_configured")
    matching = [f for f in findings if f.rule == "SQL106"]
    assert matching == []

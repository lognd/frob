"""frob.sql._sqlfluff_plugin coverage (T-5335): each of Frob_L001-
Frob_L004 fires on its planted anti-pattern and stays silent on the
paired clean query -- proves the plugin registers into sqlfluff's own
`Linter` (the same `sqlfluff` entry-point group `pyproject.toml`
declares) and that each rule's `_eval` matches the segment shape it
claims to.

frob:ticket T-5335
"""

from __future__ import annotations

import pytest

sqlfluff = pytest.importorskip(
    "sqlfluff",
    reason="sqlfluff is the `sql` extra (T-5335 OWNER "
    "DIRECTIVE: REQUIRED_FOR_FAMILY, not a core dependency)",
)

from sqlfluff.core import Linter  # noqa: E402


def _violation_codes(sql: str) -> list[str]:
    """Every rule code sqlfluff reports for `sql` when only frob's own
    `Frob_L001`-`Frob_L004` plugin rules are enabled -- the shared harness
    every test below uses so each assertion reads as "this code did/did
    not fire", not raw `Linter` plumbing repeated per test."""
    linter = Linter(
        dialect="ansi",
        rules=["Frob_L001", "Frob_L002", "Frob_L003", "Frob_L004"],
    )
    result = linter.lint_string(sql)
    return [v.rule_code() for v in result.violations]


# frob:tests src/frob/sql/_sqlfluff_plugin.py::Rule_Frob_L001 kind="unit"
# frob:tests src/frob/sql/_sqlfluff_plugin.py::get_configs_info kind="integration"  # noqa: E501
# frob:tests src/frob/sql/_sqlfluff_plugin.py::load_default_config kind="integration"  # noqa: E501
def test_select_star_is_flagged() -> None:
    """Positive control: a bare `SELECT *` fires Frob_L001."""
    assert "Frob_L001" in _violation_codes("SELECT * FROM foo;")


# frob:tests src/frob/sql/_sqlfluff_plugin.py::Rule_Frob_L001 kind="unit"
def test_named_columns_are_not_flagged() -> None:
    """A query naming its columns never fires Frob_L001."""
    assert "Frob_L001" not in _violation_codes("SELECT id, name FROM foo;")


# frob:tests src/frob/sql/_sqlfluff_plugin.py::Rule_Frob_L002 kind="unit"
@pytest.mark.parametrize("sql", ["UPDATE foo SET x = 1;", "DELETE FROM foo;"])
def test_update_delete_without_where_is_flagged(sql: str) -> None:
    """Positive control: an unqualified UPDATE/DELETE fires Frob_L002."""
    assert "Frob_L002" in _violation_codes(sql)


# frob:tests src/frob/sql/_sqlfluff_plugin.py::Rule_Frob_L002 kind="unit"
@pytest.mark.parametrize(
    "sql", ["UPDATE foo SET x = 1 WHERE id = 5;", "DELETE FROM foo WHERE id = 5;"]
)
def test_update_delete_with_where_is_not_flagged(sql: str) -> None:
    """A qualified UPDATE/DELETE never fires Frob_L002."""
    assert "Frob_L002" not in _violation_codes(sql)


# frob:tests src/frob/sql/_sqlfluff_plugin.py::Rule_Frob_L003 kind="unit"
def test_having_without_aggregate_is_flagged() -> None:
    """Positive control: HAVING with no aggregate function fires Frob_L003."""
    sql = "SELECT a FROM foo GROUP BY a HAVING a > 1;"
    assert "Frob_L003" in _violation_codes(sql)


# frob:tests src/frob/sql/_sqlfluff_plugin.py::Rule_Frob_L003 kind="unit"
def test_having_with_aggregate_is_not_flagged() -> None:
    """HAVING filtering on an aggregate never fires Frob_L003."""
    sql = "SELECT a, count(*) FROM foo GROUP BY a HAVING count(*) > 1;"
    assert "Frob_L003" not in _violation_codes(sql)


# frob:tests src/frob/sql/_sqlfluff_plugin.py::Rule_Frob_L004 kind="unit"
def test_offset_pagination_is_flagged() -> None:
    """Positive control: LIMIT ... OFFSET fires Frob_L004."""
    sql = "SELECT id FROM foo ORDER BY id LIMIT 10 OFFSET 20;"
    assert "Frob_L004" in _violation_codes(sql)


# frob:tests src/frob/sql/_sqlfluff_plugin.py::Rule_Frob_L004 kind="unit"
def test_limit_without_offset_is_not_flagged() -> None:
    """A plain LIMIT with no OFFSET never fires Frob_L004."""
    sql = "SELECT id FROM foo ORDER BY id LIMIT 10;"
    assert "Frob_L004" not in _violation_codes(sql)


# frob:tests src/frob/sql/_sqlfluff_plugin.py::get_rules kind="unit"
def test_get_rules_registers_all_four() -> None:
    """`get_rules` returns exactly the four plugin rule classes this
    leaf ships -- the fan-out `_eval` tests above each cover, listed
    once here as a registration-completeness check."""
    from frob.sql._sqlfluff_plugin import get_rules

    codes = {rule.__name__ for rule in get_rules()}
    assert codes == {
        "Rule_Frob_L001",
        "Rule_Frob_L002",
        "Rule_Frob_L003",
        "Rule_Frob_L004",
    }

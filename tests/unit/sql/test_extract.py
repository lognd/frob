"""frob.sql._extract coverage (T-5334): one extraction case per host-
language/ORM call shape, plus the WEBSEC107 injection finding and the
`sql_relevance` predicate.

frob:ticket T-5334
"""

from __future__ import annotations

from pathlib import Path

from frob.sql._extract import (
    extract_sql_literals,
    sql_injection_findings,
    sql_relevance,
)

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "sql"


# frob:tests src/frob/sql/_extract.py::extract_sql_literals kind="unit"
# frob:tests src/frob/sql/_extract.py::SqlLiteralExtraction kind="unit"  # noqa: E501
def test_extract_sql_literals_python_cursor_execute() -> None:
    """A literal DB-API cursor.execute() string is extracted verbatim."""
    extractions = extract_sql_literals(_FIXTURE_ROOT)
    matching = [
        e
        for e in extractions
        if e.file.endswith("cursor_execute_literal.py")
        and e.call_kind == "python.execute"
    ]
    assert len(matching) == 1, extractions
    assert matching[0].is_literal is True
    assert "SELECT id, name FROM users" in matching[0].sql_text


# frob:tests src/frob/sql/_extract.py::extract_sql_literals kind="unit"
def test_extract_sql_literals_python_django_raw() -> None:
    """A literal Django QuerySet.raw() string is extracted verbatim."""
    extractions = extract_sql_literals(_FIXTURE_ROOT)
    matching = [
        e
        for e in extractions
        if e.file.endswith("django_queryset_raw.py") and e.call_kind == "python.raw"
    ]
    assert len(matching) == 1, extractions
    assert matching[0].is_literal is True


# frob:tests src/frob/sql/_extract.py::extract_sql_literals kind="unit"
def test_extract_sql_literals_python_sqlalchemy_text() -> None:
    """A literal SQLAlchemy text() argument is extracted verbatim."""
    extractions = extract_sql_literals(_FIXTURE_ROOT)
    matching = [
        e
        for e in extractions
        if e.file.endswith("sqlalchemy_text.py")
        and e.call_kind == "python.sqlalchemy_text"
    ]
    assert len(matching) == 1, extractions
    assert matching[0].is_literal is True


# frob:tests src/frob/sql/_extract.py::extract_sql_literals kind="unit"
def test_extract_sql_literals_ts_prisma_query_raw() -> None:
    """A literal Prisma $queryRaw tagged-template string is extracted
    verbatim."""
    extractions = extract_sql_literals(_FIXTURE_ROOT)
    matching = [
        e
        for e in extractions
        if e.file.endswith("prisma_query_raw_literal.ts")
        and e.call_kind == "ts.prisma_queryRaw"
    ]
    assert len(matching) == 1, extractions
    assert matching[0].is_literal is True
    assert "count(*)" in matching[0].sql_text


# frob:tests src/frob/sql/_extract.py::extract_sql_literals kind="unit"
def test_extract_sql_literals_rust_sqlx_query_macro() -> None:
    """A literal sqlx query! macro string is extracted verbatim."""
    extractions = extract_sql_literals(_FIXTURE_ROOT)
    matching = [
        e
        for e in extractions
        if e.file.endswith("sqlx_query_literal.rs") and e.call_kind == "rust.sqlx_query"
    ]
    assert len(matching) == 1, extractions
    assert matching[0].is_literal is True


# frob:tests src/frob/sql/_extract.py::sql_injection_findings kind="unit"
# frob:tests src/frob/sql/_extract.py::SqlInjectionFinding kind="unit"  # noqa: E501
def test_sql_injection_findings_python_fstring_positive() -> None:
    """A non-literal, f-string-composed cursor.execute() argument plants
    exactly one WEBSEC107 finding."""
    findings = sql_injection_findings(_FIXTURE_ROOT)
    matching = [
        f
        for f in findings
        if f.file.endswith("cursor_execute_injection.py") and f.rule == "WEBSEC107"
    ]
    assert len(matching) == 1, findings


# frob:tests src/frob/sql/_extract.py::sql_injection_findings kind="unit"
def test_sql_injection_findings_python_literal_negative() -> None:
    """A literal cursor.execute() argument plants no WEBSEC107 finding."""
    findings = sql_injection_findings(_FIXTURE_ROOT)
    matching = [
        f
        for f in findings
        if f.file.endswith("cursor_execute_literal.py") and f.rule == "WEBSEC107"
    ]
    assert matching == [], findings


# frob:tests src/frob/sql/_extract.py::sql_injection_findings kind="unit"
def test_sql_injection_findings_psycopg_composition_excluded() -> None:
    """psycopg's sql.SQL/.Identifier composition is explicitly excluded
    from WEBSEC107, even though its argument is non-literal."""
    findings = sql_injection_findings(_FIXTURE_ROOT)
    matching = [
        f
        for f in findings
        if f.file.endswith("psycopg_sql_composition_safe.py") and f.rule == "WEBSEC107"
    ]
    assert matching == [], findings


# frob:tests src/frob/sql/_extract.py::sql_injection_findings kind="unit"
def test_sql_injection_findings_ts_prisma_template_positive() -> None:
    """An interpolated Prisma $queryRaw tagged template plants exactly
    one WEBSEC107 finding."""
    findings = sql_injection_findings(_FIXTURE_ROOT)
    matching = [
        f
        for f in findings
        if f.file.endswith("prisma_query_raw_injection.ts") and f.rule == "WEBSEC107"
    ]
    assert len(matching) == 1, findings


# frob:tests src/frob/sql/_extract.py::sql_injection_findings kind="unit"
def test_sql_injection_findings_ts_prisma_literal_negative() -> None:
    """A literal Prisma $queryRaw tagged template plants no WEBSEC107
    finding."""
    findings = sql_injection_findings(_FIXTURE_ROOT)
    matching = [
        f
        for f in findings
        if f.file.endswith("prisma_query_raw_literal.ts") and f.rule == "WEBSEC107"
    ]
    assert matching == [], findings


# frob:tests src/frob/sql/_extract.py::sql_relevance kind="unit"
def test_sql_relevance_true_for_call_site_fixture() -> None:
    """The fixture directory itself has SQL-executing call sites, so the
    relevance predicate reports True."""
    assert sql_relevance(_FIXTURE_ROOT) is True


# frob:tests src/frob/sql/_extract.py::sql_relevance kind="unit"
def test_sql_relevance_false_for_plain_repo(tmp_path: Path) -> None:
    """A directory with no `.sql` file and no SQL-executing call site
    reports relevance False (this is what makes sqlfluff's absence
    'unmeasured' rather than failing, per the owner directive)."""
    (tmp_path / "app.py").write_text("print('hello')\n", encoding="utf-8")
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    assert sql_relevance(tmp_path) is False

"""PII010: Python data-structure field-name/type scan (T-0207 family 1) and
DB/DDL schema scan (T-0348 family 2: sqlalchemy ORM columns, raw-SQL
`CREATE TABLE` string literals) -- T-1076 split of `frob.gates.
_pii_structural`."""

from __future__ import annotations

import ast
import re

from frob.gates._models import Severity, Violation
from frob.logging import get_logger

from ._declared_surface import _EMPTY_DECLARED_SURFACE, _DeclaredSurface
from ._signatures import _field_name_hit, _field_type_hit

_log = get_logger(__name__)

#: Base-class / decorator name fragments that mark a `ClassDef` as a data
#: structure worth scanning (pydantic `BaseModel`, `TypedDict`,
#: `NamedTuple`, `dataclasses.dataclass`, `attrs`/`attr.s` `define`). T-0971
#: (gates-quality audit finding 14): a `class User(OrmBase)` subclassing a
#: PROJECT-LOCAL intermediate base (not `BaseModel` itself) was invisible
#: -- the exact shape SQLAlchemy's declarative pattern and Django's ORM
#: both use, arguably the most common real PII carrier (an ORM row).
#: `DeclarativeBase` (SQLAlchemy 2.0's own base, `class Base(DeclarativeBase)`
#: is the documented idiom so a project's `Base` is one hop from this name,
#: not zero) and `Model` (Django's `models.Model`, matched on the bare
#: `Attribute.attr` suffix the same way `BaseModel`/`TypedDict` already
#: are) are added directly since they are fixed, well-known library names.
#: A THIRD-hop project-local base (`class User(OrmBase)` where `OrmBase`
#: itself subclasses `DeclarativeBase`) is NOT resolved -- that needs
#: cross-file base-class transitive resolution this AST-local, single-file
#: gate does not have; disclosed as a real remaining gap, not silently
#: dropped (T-0971 Done report).
# frob:ticket T-0971
# frob:tests tests/test_pii_structural_gate.py::TestFieldNames.test_orm_declarative_base_field_fires  # noqa: E501
_STRUCTURE_BASE_NAMES = frozenset(
    {"BaseModel", "TypedDict", "NamedTuple", "DeclarativeBase", "Model"}
)
_STRUCTURE_DECORATOR_NAMES = frozenset({"dataclass", "define", "attrs", "frozen"})


def _decorator_name(node: ast.expr) -> str | None:
    """The bare name of a decorator expression (`@dataclass` -> `dataclass`,
    `@attr.s` -> `s`, `@dataclasses.dataclass(frozen=True)` -> `dataclass`),
    or `None` for a shape this doesn't recognize."""
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return None


def _is_data_structure(cls: ast.ClassDef) -> bool:
    """Whether `cls` is a pydantic/dataclass/TypedDict/NamedTuple/attrs data
    structure -- the population PII010 scans field names/types over."""
    for base in cls.bases:
        base_name = (
            base.id if isinstance(base, ast.Name) else getattr(base, "attr", None)
        )
        if base_name in _STRUCTURE_BASE_NAMES:
            return True
    for decorator in cls.decorator_list:
        name = _decorator_name(decorator)
        if name in _STRUCTURE_DECORATOR_NAMES:
            return True
    return False


def _pii010_violation(rel_path: str, lineno: int, field_name: str, sig) -> Violation:  # noqa: ANN001
    """The PII010 `Violation` for one PII-shaped field, built once so both
    the name-hit and type-hit call sites share identical message wording."""
    _log.warning(
        "PII010: %s:%d field %r matches %s (%s) -- category %s",
        rel_path,
        lineno,
        field_name,
        sig.id,
        sig.kind,
        sig.category,
    )
    return Violation(
        rule="PII010",
        severity=Severity.WARN,
        file=rel_path,
        line=lineno,
        message=(
            f"PII010: {rel_path}:{lineno} field {field_name!r} is PII-shaped "
            f"(matches {sig.kind} signature {sig.keyword!r}, category "
            f"{sig.category!r}) with no PII declaration or waiver -- declare "
            f"it via a std.pii `carries` tag on the owning strata node, or "
            f'`frob:waive PII010 reason="..."` if this field is not '
            f"actually personal data"
        ),
    )


def _scan_class_fields(
    cls: ast.ClassDef,
    rel_path: str,
    declared: _DeclaredSurface = _EMPTY_DECLARED_SURFACE,
) -> list[Violation]:
    """Every PII010 hit among `cls`'s direct `AnnAssign` fields, for a class
    `_is_data_structure` already accepted -- skipping any field whose
    category `declared` (T-0351) already `carries` for this file."""
    violations: list[Violation] = []
    for stmt in cls.body:
        if not isinstance(stmt, ast.AnnAssign) or not isinstance(stmt.target, ast.Name):
            continue
        field_name = stmt.target.id
        name_sig = _field_name_hit(field_name)
        type_sig = _field_type_hit(stmt.annotation)
        sig = name_sig or type_sig
        if sig is not None and not declared._has_pii(rel_path, sig.category):
            violations.append(_pii010_violation(rel_path, stmt.lineno, field_name, sig))
    return violations


# frob:tests tests/test_pii_structural_gate.py::TestFieldNames.test_password_field_fires
def _scan_python_fields(
    tree: ast.Module,
    rel_path: str,
    declared: _DeclaredSurface = _EMPTY_DECLARED_SURFACE,
) -> tuple[Violation, ...]:
    """PII010 over every data-structure `ClassDef` in `tree` (module
    docstring: pydantic/dataclass/TypedDict/attrs field names+types),
    joined against `declared`'s std.pii carries tags (T-0351)."""
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and _is_data_structure(node):
            violations.extend(_scan_class_fields(node, rel_path, declared))
    return tuple(violations)


#: `Column(...)`/`sa.Column(...)` call-name fragment (family 2, T-0348):
#: sqlalchemy ORM declarative-model column declarations. Matched on the
#: bare dotted-suffix, same posture as `_decorator_name`'s bare-name match
#: (no import-alias resolution attempted -- a local, testable surface).
_COLUMN_CALL_NAME = "Column"


def _is_column_call(node: ast.Call) -> bool:
    """Whether `node` is a `Column(...)`/`sa.Column(...)`/`sqlalchemy.
    Column(...)` call (T-0348 family 2: sqlalchemy ORM column declarations)."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == _COLUMN_CALL_NAME
    if isinstance(func, ast.Attribute):
        return func.attr == _COLUMN_CALL_NAME
    return False


def _literal_str(node: ast.expr | None) -> str | None:
    """The literal string value of `node` if it is a bare `ast.Constant`
    string, else `None` -- used to statically name a value when the
    argument/subscript key is a literal, never guessed from a dynamic
    expression."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _column_call_string_name(node: ast.Call) -> str | None:
    """The literal column-name string of an alembic-style positional
    `Column("name", ...)` / `sa.Column("name", ...)` call (`op.create_
    table`'s column-list form), or `None` if the first arg is not a bare
    string literal (e.g. the ORM declarative form, which has no name arg
    at all -- the assignment target name covers that case instead)."""
    if not node.args:
        return None
    return _literal_str(node.args[0])


def _scan_orm_columns(
    tree: ast.Module,
    rel_path: str,
    declared: _DeclaredSurface = _EMPTY_DECLARED_SURFACE,
) -> list[Violation]:
    """PII010 over `name = Column(...)` declarative-model assignments and
    `Column("name", ...)` alembic-style positional column declarations
    (T-0348 family 2), matched against `FIELD_SIGNATURES` the same way a
    dataclass/pydantic field name is; joined against `declared` (T-0351)."""
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and _is_column_call(node)):
            continue
        string_name = _column_call_string_name(node)
        if string_name is not None:
            sig = _field_name_hit(string_name)
            if sig is not None and not declared._has_pii(rel_path, sig.category):
                violations.append(
                    _pii010_violation(rel_path, node.lineno, string_name, sig)
                )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not (isinstance(node.value, ast.Call) and _is_column_call(node.value)):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                sig = _field_name_hit(target.id)
                if sig is not None and not declared._has_pii(rel_path, sig.category):
                    violations.append(
                        _pii010_violation(rel_path, node.lineno, target.id, sig)
                    )
    return violations


#: `CREATE TABLE ... (col1 TYPE, col2 TYPE, ...)` column-list extraction
#: (T-0348 family 2: raw SQL DDL embedded as a Python string literal, e.g.
#: a raw-SQL alembic migration's `op.execute("CREATE TABLE ...")`).
_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+[\"'`]?\w+[\"'`]?\s*\((.*)\)", re.IGNORECASE | re.DOTALL
)


def _split_top_level_commas(body: str) -> list[str]:
    """Split a `CREATE TABLE(...)` column-list body on top-level commas
    only -- commas nested inside a `CHECK(...)`/`DEFAULT(...)`/type-param
    parenthesized clause (e.g. `NUMERIC(10, 2)`) must not split a single
    column definition in two."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in body:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


#: DDL table-constraint keywords a column-list entry may start with instead
#: of a column name (`PRIMARY KEY (...)`, `FOREIGN KEY (...)`, etc.) -- these
#: are not column names and must not be matched against `FIELD_SIGNATURES`.
_DDL_CONSTRAINT_KEYWORDS = frozenset(
    {"PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT"}
)


def _ddl_column_names(sql: str) -> list[str]:
    """Every column NAME token in the first `CREATE TABLE(...)` statement
    found in `sql`, skipping table-constraint entries (`_DDL_CONSTRAINT_
    KEYWORDS`) -- a small structural parse, not a full SQL grammar (module
    docstring precedent: `_pii_structural` favors a targeted, testable
    surface over a general parser)."""
    match = _CREATE_TABLE_RE.search(sql)
    if match is None:
        return []
    names: list[str] = []
    for entry in _split_top_level_commas(match.group(1)):
        tokens = entry.strip().split()
        if not tokens:
            continue
        first = tokens[0].strip('"`[]')
        if first.upper() in _DDL_CONSTRAINT_KEYWORDS:
            continue
        names.append(first)
    return names


def _scan_ddl_strings(
    tree: ast.Module,
    rel_path: str,
    declared: _DeclaredSurface = _EMPTY_DECLARED_SURFACE,
) -> list[Violation]:
    """PII010 over `CREATE TABLE` column names embedded in string-literal
    constants anywhere in `tree` (T-0348 family 2: raw-SQL migrations),
    joined against `declared` (T-0351)."""
    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        for column_name in _ddl_column_names(node.value):
            sig = _field_name_hit(column_name)
            if sig is not None and not declared._has_pii(rel_path, sig.category):
                violations.append(
                    _pii010_violation(rel_path, node.lineno, column_name, sig)
                )
    return violations


# frob:tests tests/test_pii_structural_gate.py::TestDdlSchema.test_orm_column_password_fires  # noqa: E501
def _scan_python_ddl(
    tree: ast.Module,
    rel_path: str,
    declared: _DeclaredSurface = _EMPTY_DECLARED_SURFACE,
) -> tuple[Violation, ...]:
    """PII010 over sqlalchemy ORM `Column(...)` declarations and raw-SQL
    `CREATE TABLE` string literals (T-0348 family 2: DB/DDL schema
    scanning, deferred from T-0207)."""
    violations = _scan_orm_columns(tree, rel_path, declared)
    violations.extend(_scan_ddl_strings(tree, rel_path, declared))
    return tuple(violations)


def _is_data_structure_field_target(node: ast.AST) -> bool:
    """Whether `node` is the `Name` target of an `AnnAssign` field already
    covered by PII010 (`_scan_class_fields`) -- excluded from the family-5
    keyword sweep so the same field name is not reported twice under two
    different rule ids for the identical site."""
    return (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and _field_name_hit(node.target.id) is not None
    )

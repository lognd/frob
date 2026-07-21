"""Tests for frob.gates._pii_structural -- PII010/SEC110
(docs/modules/gates.md#structural-pii-secrets-detection-t-0207).

Fixture snippets below are synthetic (`tempfile`-backed git repos or direct
`ast.parse` calls over inline source strings), never real credentials --
same posture as `tests/test_secrets_gate.py`.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest

from frob.gates._models import Severity
from frob.gates._pii_structural import (
    FIELD_SIGNATURES,
    _is_data_structure,
    _is_email_shaped,
    _load_declared_surface,
    _scan_python_ddl,
    _scan_python_email_values,
    _scan_python_env_access,
    _scan_python_fields,
    _scan_python_keyword_sweep,
    pii_structural_gate,
)


# frob:waive DUP001 reason="parallel test fixtures across 3 sibling test \
# file(s) (3 sites) sharing an arrange-act scaffold typical of exhaustive \
# per-case/per-scenario coverage; extracting would obscure per-case intent"
def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "checkout", "-q", "-b", "main")


def _commit(root: Path, message: str = "commit") -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


class TestFieldNames:
    """PII010: field-name/type detection over Python data structures."""

    # frob:waive DUP001 reason="parallel test methods within \
    # test_pii_structural_gate.py (2 sites) sharing an arrange-act scaffold \
    # typical of exhaustive per-case coverage; extracting would obscure \
    # per-case intent"
    def test_password_field_fires(self) -> None:
        # frob:tests src/frob/gates/_pii_structural.py::_scan_python_fields
        src = (
            "from dataclasses import dataclass\n\n"
            "@dataclass\n"
            "class User:\n"
            "    password: str\n"
        )
        tree = ast.parse(src)
        violations = _scan_python_fields(tree, "example.py")
        assert any(v.rule == "PII010" for v in violations)

    # frob:waive DUP001 reason="parallel test methods within \
    # test_pii_structural_gate.py (2 sites) sharing an arrange-act scaffold \
    # typical of exhaustive per-case coverage; extracting would obscure \
    # per-case intent"
    def test_pydantic_email_type_fires(self) -> None:
        src = (
            "from pydantic import BaseModel, EmailStr\n\n"
            "class User(BaseModel):\n"
            "    contact: EmailStr\n"
        )
        tree = ast.parse(src)
        violations = _scan_python_fields(tree, "example.py")
        assert any(v.rule == "PII010" for v in violations)

    def test_typeddict_ssn_field_fires(self) -> None:
        src = "from typing import TypedDict\n\nclass Record(TypedDict):\n    ssn: str\n"
        tree = ast.parse(src)
        violations = _scan_python_fields(tree, "example.py")
        assert any(v.rule == "PII010" for v in violations)

    def test_plain_class_not_scanned(self) -> None:
        """A non-dataclass/pydantic/TypedDict class with a `password`-named
        attribute is not a data structure per `_is_data_structure` -- no
        false positive on an ordinary helper class."""
        src = "class Helper:\n    password: str\n"
        tree = ast.parse(src)
        cls = tree.body[0]
        assert isinstance(cls, ast.ClassDef)
        assert not _is_data_structure(cls)

    def test_unrelated_field_name_does_not_fire(self) -> None:
        src = (
            "from dataclasses import dataclass\n\n"
            "@dataclass\n"
            "class Widget:\n"
            "    width: int\n"
            "    height: int\n"
        )
        tree = ast.parse(src)
        violations = _scan_python_fields(tree, "example.py")
        assert violations == ()

    def test_tokenizer_field_does_not_falsely_match_token(self) -> None:
        """`_field_name_hit`'s single-word token match: a field literally
        named `tokenizer` must not fire on the `token` keyword (whole-token
        match, not substring) -- T-0219-style false-positive discipline."""
        src = (
            "from dataclasses import dataclass\n\n"
            "@dataclass\n"
            "class Pipeline:\n"
            "    tokenizer: str\n"
        )
        tree = ast.parse(src)
        violations = _scan_python_fields(tree, "example.py")
        assert violations == ()


class TestEnvAccess:
    """SEC110: os.environ/os.getenv access-site detection."""

    def test_os_getenv_fires(self) -> None:
        # frob:tests src/frob/gates/_pii_structural.py::_scan_python_env_access
        src = "import os\nvalue = os.getenv('SOME_VAR')\n"
        tree = ast.parse(src)
        violations = _scan_python_env_access(tree, "example.py")
        assert any(v.rule == "SEC110" for v in violations)

    def test_os_environ_subscript_fires(self) -> None:
        src = "import os\nvalue = os.environ['SOME_VAR']\n"
        tree = ast.parse(src)
        violations = _scan_python_env_access(tree, "example.py")
        assert any(v.rule == "SEC110" for v in violations)

    def test_os_environ_get_fires(self) -> None:
        src = "import os\nvalue = os.environ.get('SOME_VAR')\n"
        tree = ast.parse(src)
        violations = _scan_python_env_access(tree, "example.py")
        assert any(v.rule == "SEC110" for v in violations)

    def test_direct_import_getenv_fires(self) -> None:
        src = "from os import getenv\nvalue = getenv('SOME_VAR')\n"
        tree = ast.parse(src)
        violations = _scan_python_env_access(tree, "example.py")
        assert any(v.rule == "SEC110" for v in violations)

    def test_unrelated_call_does_not_fire(self) -> None:
        src = "value = dict().get('SOME_VAR')\n"
        tree = ast.parse(src)
        violations = _scan_python_env_access(tree, "example.py")
        assert violations == ()


class TestDdlSchema:
    """PII010 (T-0348 family 2): sqlalchemy ORM `Column(...)` declarations
    and raw-SQL `CREATE TABLE` string literals."""

    # frob:waive DUP001 reason="parallel test methods within \
    # test_pii_structural_gate.py (2 sites) sharing an arrange-act scaffold \
    # typical of exhaustive per-case coverage; extracting would obscure \
    # per-case intent"
    def test_orm_column_password_fires(self) -> None:
        # frob:tests src/frob/gates/_pii_structural.py::_scan_python_ddl
        src = (
            "from sqlalchemy import Column, String\n\n"
            "class User(Base):\n"
            "    __tablename__ = 'users'\n"
            "    password = Column(String)\n"
        )
        tree = ast.parse(src)
        violations = _scan_python_ddl(tree, "example.py")
        assert any(v.rule == "PII010" for v in violations)

    def test_alembic_positional_column_ssn_fires(self) -> None:
        src = (
            "import sqlalchemy as sa\n"
            "from alembic import op\n\n"
            "op.create_table(\n"
            "    'users',\n"
            "    sa.Column('ssn', sa.String),\n"
            ")\n"
        )
        tree = ast.parse(src)
        violations = _scan_python_ddl(tree, "example.py")
        assert any(v.rule == "PII010" for v in violations)

    def test_raw_sql_create_table_email_fires(self) -> None:
        src = (
            "from alembic import op\n\n"
            "op.execute(\n"
            "    'CREATE TABLE users (id INTEGER PRIMARY KEY, "
            "email VARCHAR(255), age INTEGER)'\n"
            ")\n"
        )
        tree = ast.parse(src)
        violations = _scan_python_ddl(tree, "example.py")
        assert any(v.rule == "PII010" for v in violations)

    def test_raw_sql_create_table_unrelated_columns_do_not_fire(self) -> None:
        src = (
            "from alembic import op\n\n"
            "op.execute(\n"
            "    'CREATE TABLE widgets (id INTEGER PRIMARY KEY, "
            "width INTEGER, height INTEGER)'\n"
            ")\n"
        )
        tree = ast.parse(src)
        violations = _scan_python_ddl(tree, "example.py")
        assert violations == ()

    def test_orm_column_unrelated_field_does_not_fire(self) -> None:
        src = (
            "from sqlalchemy import Column, Integer\n\n"
            "class Widget(Base):\n"
            "    __tablename__ = 'widgets'\n"
            "    width = Column(Integer)\n"
        )
        tree = ast.parse(src)
        violations = _scan_python_ddl(tree, "example.py")
        assert violations == ()


class TestEmailShapeValues:
    """PII011 (T-0349 family 4): structural (non-regex, `email.utils.
    parseaddr`-based) email-shaped string-literal detection, with the
    T-0157 `frob:secret-fake` marker escape. Every email-shaped literal
    below is embedded inside a larger source snippet string, never a bare
    top-level literal in THIS test file's own source, so this module's
    own self-match exclusion is never the reason a case passes."""

    def test_is_email_shaped_accepts_plain_address(self) -> None:
        # frob:tests src/frob/gates/_pii_structural.py::_is_email_shaped
        assert _is_email_shaped("user" + "@" + "example.com")

    def test_is_email_shaped_rejects_display_name_wrapped(self) -> None:
        """A `"Name <addr>"` RFC 822 header shape is NOT treated as a bare
        email literal (module docstring's disclosed boundary): `parseaddr`
        extracts a DIFFERENT address than the full literal text."""
        assert not _is_email_shaped("Alice " + "<user@example.com>")

    def test_is_email_shaped_rejects_no_tld_dot(self) -> None:
        """`user@example` (single domain label, no dot) does not fire --
        an evasion-shaped near-miss that must stay clean."""
        assert not _is_email_shaped("user" + "@" + "example")

    def test_is_email_shaped_rejects_obfuscated_at(self) -> None:
        """`user(at)example.com` (a common obfuscation evasion) has no
        literal `@` at all, so `parseaddr` cannot extract an address --
        stays clean, an honestly-disclosed detection boundary, not a bug."""
        assert not _is_email_shaped("user(at)example.com")

    def test_is_email_shaped_rejects_plain_text(self) -> None:
        assert not _is_email_shaped("not an email at all")

    def test_email_literal_fires(self) -> None:
        # frob:tests src/frob/gates/_pii_structural.py::_scan_python_email_values  # noqa: E501
        src = "contact = " + repr("user" + "@" + "example.com") + "\n"
        tree = ast.parse(src)
        violations = _scan_python_email_values(tree, "example.py", src)
        assert any(v.rule == "PII011" for v in violations)

    def test_fake_marker_on_same_line_discharges(self) -> None:
        src = (
            "contact = " + repr("user" + "@" + "example.com") + "  # frob:secret-fake\n"
        )
        tree = ast.parse(src)
        violations = _scan_python_email_values(tree, "example.py", src)
        assert violations == ()

    def test_fake_marker_on_line_above_discharges(self) -> None:
        src = (
            "# frob:secret-fake\ncontact = " + repr("user" + "@" + "example.com") + "\n"
        )
        tree = ast.parse(src)
        violations = _scan_python_email_values(tree, "example.py", src)
        assert violations == ()

    def test_plain_string_literal_does_not_fire(self) -> None:
        src = "greeting = 'hello world'\n"
        tree = ast.parse(src)
        violations = _scan_python_email_values(tree, "example.py", src)
        assert violations == ()


class TestKeywordSweep:
    """PII012 (T-0350 family 5): identifier/comment keyword hits at
    suggestion severity, excluding sites PII010 already reports."""

    def test_identifier_keyword_fires_at_suggestion_severity(self) -> None:
        # frob:tests src/frob/gates/_pii_structural.py::_scan_python_keyword_sweep  # noqa: E501
        src = "def handler():\n    password = fetch_value()\n    return password\n"
        tree = ast.parse(src)
        violations = _scan_python_keyword_sweep(tree, "example.py", src)
        assert any(
            v.rule == "PII012" and v.severity == Severity.WARN for v in violations
        )

    def test_function_parameter_keyword_fires(self) -> None:
        src = "def handler(api_key):\n    return api_key\n"
        tree = ast.parse(src)
        violations = _scan_python_keyword_sweep(tree, "example.py", src)
        assert any(v.rule == "PII012" for v in violations)

    def test_comment_keyword_fires(self) -> None:
        src = "x = 1  # stores the user ssn for lookup\n"
        tree = ast.parse(src)
        violations = _scan_python_keyword_sweep(tree, "example.py", src)
        assert any(v.rule == "PII012" for v in violations)

    def test_unrelated_identifier_does_not_fire(self) -> None:
        src = "def handler(width, height):\n    return width + height\n"
        tree = ast.parse(src)
        violations = _scan_python_keyword_sweep(tree, "example.py", src)
        assert violations == ()

    def test_tokenizer_identifier_does_not_falsely_match_token(self) -> None:
        """Whole-token match, not substring, same T-0219 discipline PII010
        already applies -- `tokenizer` must not match the `token` keyword."""
        src = "def handler():\n    tokenizer = build()\n    return tokenizer\n"
        tree = ast.parse(src)
        violations = _scan_python_keyword_sweep(tree, "example.py", src)
        assert violations == ()

    def test_data_structure_field_not_double_reported(self) -> None:
        """A field PII010 already reports on (a `password` field in a
        `@dataclass`) is excluded from the family-5 identifier sweep --
        no double report of the identical site under two rule ids."""
        src = (
            "from dataclasses import dataclass\n\n"
            "@dataclass\n"
            "class User:\n"
            "    password: str\n"
        )
        tree = ast.parse(src)
        field_violations = _scan_python_fields(tree, "example.py")
        sweep_violations = _scan_python_keyword_sweep(tree, "example.py", src)
        assert any(v.rule == "PII010" for v in field_violations)
        assert not any(v.rule == "PII012" for v in sweep_violations)


class TestDeclaredSurfaceJoin:
    """T-0351: PII010/SEC110 findings joined against a loaded strata
    design's std.pii `carries` tags / Secret-clearance code binding --
    a real declaration discharges a finding outright, not just a waiver."""

    def test_pii010_discharged_by_matching_carries_tag(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_pii_structural.py::_load_declared_surface  # noqa: E501
        _init_repo(tmp_path)
        (tmp_path / "design").mkdir()
        (tmp_path / "design" / "join.strata").write_text(
            "module join\n\n"
            "node store_users : trusted {\n"
            "    clearance Pii;\n"
            '    carries "credentials.password";\n'
            '    code "app.py";\n'
            "}\n",
            encoding="utf-8",
        )
        (tmp_path / "app.py").write_text(
            "from dataclasses import dataclass\n\n"
            "@dataclass\n"
            "class User:\n"
            "    password: str\n",
            encoding="utf-8",
        )
        _commit(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert not any(v.rule == "PII010" for v in violations)

    def test_pii010_still_fires_when_no_declaration_covers_it(
        self, tmp_path: Path
    ) -> None:
        """A field whose category the code-bound node does NOT `carries`
        still fires -- the join discharges only a matching declaration,
        never every finding in a design-bound repo wholesale."""
        _init_repo(tmp_path)
        (tmp_path / "design").mkdir()
        (tmp_path / "design" / "join.strata").write_text(
            "module join\n\n"
            "node store_users : trusted {\n"
            "    clearance Pii;\n"
            '    carries "contact.email";\n'
            '    code "app.py";\n'
            "}\n",
            encoding="utf-8",
        )
        (tmp_path / "app.py").write_text(
            "from dataclasses import dataclass\n\n"
            "@dataclass\n"
            "class User:\n"
            "    password: str\n",
            encoding="utf-8",
        )
        _commit(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert any(v.rule == "PII010" for v in violations)

    def test_sec110_discharged_by_secret_clearance_binding(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        (tmp_path / "design").mkdir()
        (tmp_path / "design" / "join.strata").write_text(
            "module join\n\n"
            "node vault_reader : trusted {\n"
            "    clearance Secret;\n"
            '    code "reader.py";\n'
            "}\n",
            encoding="utf-8",
        )
        (tmp_path / "reader.py").write_text(
            "import os\nvalue = os.getenv('SOME_VAR')\n", encoding="utf-8"
        )
        _commit(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert not any(v.rule == "SEC110" for v in violations)

    def test_sec110_still_fires_with_no_design_directory(self, tmp_path: Path) -> None:
        """No `design/` directory at all -- `_load_declared_surface`
        degrades to the empty surface, every finding fires exactly as
        before T-0351 (waiver-only discharge)."""
        _init_repo(tmp_path)
        (tmp_path / "reader.py").write_text(
            "import os\nvalue = os.getenv('SOME_VAR')\n", encoding="utf-8"
        )
        _commit(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert any(v.rule == "SEC110" for v in violations)

    def test_load_declared_surface_empty_with_no_design_dir(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        (tmp_path / "placeholder.py").write_text("x = 1\n", encoding="utf-8")
        _commit(tmp_path)
        declared = _load_declared_surface(tmp_path)
        assert not declared._has_pii("anything.py", "identifier")
        assert not declared._has_secret("anything.py")


class TestSelfMatchExclusion:
    """T-0201 lesson: the registry file must not detect itself."""

    def test_own_file_not_scanned(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        src_dir = tmp_path / "src" / "frob" / "gates"
        src_dir.mkdir(parents=True)
        module_path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "frob"
            / "gates"
            / "_pii_structural.py"
        )
        (src_dir / "_pii_structural.py").write_text(
            module_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
        _commit(tmp_path)
        violations = pii_structural_gate(tmp_path)
        assert not any(
            v.file == "src/frob/gates/_pii_structural.py" for v in violations
        )


class TestGateIsGreenOnItself:
    """The gate must never flag its own module path, even when it is the
    only tracked file (belt-and-suspenders on top of `TestSelfMatchExclusion`
    exercising the real module source, not a copy)."""

    def test_own_module_source_produces_no_self_finding(self) -> None:
        # frob:tests src/frob/gates/_pii_structural.py::pii_structural_gate
        root = Path(__file__).resolve().parents[1]
        violations = pii_structural_gate(root)
        assert not any(
            v.file == "src/frob/gates/_pii_structural.py" for v in violations
        )


class TestDriftLock:
    """T-0182-style per-entry drift-lock: every `FIELD_SIGNATURES` entry
    must fire against a synthetic fixture built from its own keyword --
    a registry entry with no firing fixture fails here immediately."""

    @pytest.mark.parametrize("sig", FIELD_SIGNATURES, ids=lambda sig: sig.id)
    def test_signature_fires(self, sig) -> None:  # noqa: ANN001
        if sig.kind == "name":
            field_name = sig.keyword if "_" in sig.keyword else f"{sig.keyword}_value"
            src = (
                "from dataclasses import dataclass\n\n"
                "@dataclass\n"
                "class Fixture:\n"
                f"    {field_name}: str\n"
            )
        else:
            src = (
                "from dataclasses import dataclass\n\n"
                "@dataclass\n"
                "class Fixture:\n"
                f"    value: {sig.keyword}\n"
            )
        tree = ast.parse(src)
        violations = _scan_python_fields(tree, "fixture.py")
        matched = [v for v in violations if sig.keyword in v.message]
        assert matched, f"signature {sig.id!r} did not fire against its own fixture"

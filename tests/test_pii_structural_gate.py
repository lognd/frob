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

from frob.gates._pii_structural import (
    FIELD_SIGNATURES,
    _is_data_structure,
    _scan_python_env_access,
    _scan_python_fields,
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

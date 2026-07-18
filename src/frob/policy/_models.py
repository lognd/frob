"""Data shapes for frob.policy (docs/modules/gates.md's Policy rules section)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet

__all__ = ["PolicyError", "PolicyKind", "PolicyRule"]


# frob:doc docs/modules/gates.md#policy-rules-frobtoml-policy
class PolicyKind(StrEnum):
    """The three rule kinds `frob.toml`'s `[policy]` table supports at alpha."""

    FORBIDDEN_IMPORT = "forbidden-import"
    PATTERN = "pattern"
    NORM = "norm"


# frob:doc docs/modules/gates.md#policy-rules-frobtoml-policy
class PolicyRule(BaseModel):
    """One `[[policy.<kind>]]` entry; fields not used by `kind` are left default."""

    model_config = ConfigDict(frozen=True)

    id: str
    kind: PolicyKind
    severity: str = "error"
    reason: str = ""

    # forbidden-import
    module: str = ""
    within: str = ""

    # pattern
    language: str = ""
    query: str = ""
    query_file: str = ""
    globs: tuple[str, ...] = ()

    # norm
    max_diff_lines: int = 0


# frob:doc docs/modules/gates.md#error-types
class PolicyError(ErrorSet):
    """Failure values `frob.policy`'s loading and matching paths can return."""

    MalformedRule = "Policy rule failed schema validation"
    BadQuery = "tree-sitter query does not compile"

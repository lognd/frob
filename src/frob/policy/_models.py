"""Data shapes for frob.policy (docs/modules/gates.md's Policy rules section)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet

__all__ = [
    "CommandEntry",
    "CommandStep",
    "CommandsConfig",
    "CommandsError",
    "PolicyError",
    "PolicyKind",
    "PolicyRule",
]


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


# frob:doc docs/commands/run.md#commands-table
# frob:ticket T-4759
CommandStep = str | tuple[str, ...]
"""One step of a resolved `[commands]` entry: either the name of another
entry to run in its place (composition), or a literal shell-free argv
(a tuple of tokens run with no shell involved)."""


# frob:doc docs/commands/run.md#commands-table
# frob:ticket T-4759
class CommandEntry(BaseModel):
    """One `frob.toml` `[commands]` entry, normalized to an ordered tuple
    of steps -- a bare single command is normalized to a one-step tuple
    so `frob run`/`frob build` always walk the same shape."""

    model_config = {}

    steps: tuple[CommandStep, ...]


# frob:doc docs/commands/run.md#commands-table
# frob:ticket T-4759
# tests/unit/test_run_commands.py::TestLoadCommands.test_three_step_sequence_composes
class CommandsConfig(BaseModel):
    """Every `[commands]` entry declared in `frob.toml`, keyed by name --
    the parsed, cycle-checked shape `frob run`/`frob build` resolve
    against (docs/commands/run.md is authoritative)."""

    model_config = {}

    entries: dict[str, CommandEntry] = {}


# frob:doc docs/commands/run.md#error-types
# frob:ticket T-4759
# tests/unit/test_run_commands.py::TestLoadCommands.test_self_reference_refused_with_path  # noqa: E501
class CommandsError(ErrorSet):
    """Failure values loading/resolving `frob.toml`'s `[commands]` table
    can return."""

    MalformedEntry = "a [commands] entry failed schema validation"
    CycleDetected = "a command entry references itself, directly or transitively"

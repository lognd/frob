"""Typed CLI operand parsing for `frob refactor`'s verbs (T-2990).

A symbol reference, a module reference, and a file path are three
DISTINCT operand kinds. Before this module, `move`/`rename` fed a raw
`MODULE:QUALNAME` string straight into `SymbolRef` with no structural
guard against a caller handing a shared engine something else entirely
(a bare module, or a filesystem path) -- `frob refactor move app:run
attachments/img.jpg` had nothing stopping it from being ACCEPTED and
misinterpreted. `classify_operand` parses a raw string into an
`OperandKind` up front; `parse_symbol_operand`/`parse_module_operand`
each refuse (typed `Err(OperandError.WrongOperandKind)`, no tree write)
when the text does not match their own declared kind, rather than
guessing. `validate_module_destination` is the second half of the same
guard: a MODULE-kind operand that parses fine can still name an illegal
Python module location (outside the source root, a non-identifier path
segment, an already-occupied destination) -- refused here, before any
file is touched.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani import Err, Ok
from typani.error_set import ErrorSet
from typani.result import Result

from frob.refactor._models import SymbolRef

__all__ = [
    "ModuleRef",
    "OperandError",
    "OperandKind",
    "classify_operand",
    "parse_module_operand",
    "parse_symbol_operand",
    "validate_module_destination",
]


# frob:doc docs/commands/refactor.md#operandkind
# frob:tests tests/test_refactor.py::TestOperands.test_classifies_symbol_module_and_path
class OperandKind(StrEnum):
    """The three operand kinds a raw CLI argument classifies into --
    SYMBOL (`module:qualname`), MODULE (a bare dotted path), or PATH (a
    filesystem-shaped fragment, unusable by any verb but named so a
    refusal can say what it saw instead of just that it failed)."""

    SYMBOL = "symbol"
    MODULE = "module"
    PATH = "path"


# frob:doc docs/commands/refactor.md#operanderror
# frob:tests tests/test_refactor.py::TestOperands.test_parse_symbol_operand_refuses_module_shaped  # noqa: E501
class OperandError(ErrorSet):
    """Operand-typing refusals (T-2990) -- distinct from `RefactorError`,
    which is a pipeline-PHASE failure (dirty tree, unresolved target).
    These are OPERAND-SHAPE failures: caught before Resolve ever runs,
    every one of them leaves the tree byte-identical."""

    WrongOperandKind = (
        "operand does not match the kind this verb accepts "
        "(symbol `module:qualname` / module `dotted.path` / file path)"
    )
    InvalidDestination = (
        "destination is not a legal Python module location (must be inside a "
        "declared source root, end in .py, and have a valid identifier for "
        "every path segment)"
    )
    DestinationExists = (
        "destination module already exists; refusing without an explicit "
        "collision policy"
    )


# frob:doc docs/commands/refactor.md#moduleref
# frob:tests tests/test_refactor.py::TestOperands.test_parse_module_operand_refuses_symbol_shaped  # noqa: E501
class ModuleRef(BaseModel):
    """A dotted Python module path operand (T-2990) -- the MODULE operand
    kind. Deliberately NOT a `SymbolRef`: a `SymbolRef` additionally
    carries a `qualname`, and giving a module verb a `SymbolRef`-shaped
    value (or vice versa) is exactly the operand-kind confusion this
    typed split exists to make inexpressible."""

    model_config = ConfigDict(frozen=True)

    module: str


def _is_dotted_identifier_chain(text: str) -> bool:
    """`True` iff every `.`-separated segment of `text` is a valid Python
    identifier and there is at least one segment -- the shape test both
    `classify_operand` (MODULE kind) and `validate_module_destination`
    (destination legality) share."""
    if not text:
        return False
    segments = text.split(".")
    return all(seg.isidentifier() for seg in segments)


# frob:doc docs/commands/refactor.md#classify_operand
# frob:tests tests/test_refactor.py::TestOperands.test_classifies_symbol_module_and_path  # noqa: E501
def classify_operand(text: str) -> OperandKind:
    """Classify a raw CLI operand string into an `OperandKind` value by
    SHAPE alone, before any resolution: PATH if it contains a path
    separator (the `attachments/img.jpg` shape -- a symbol/module operand
    is never spelled with a `/`), SYMBOL if it contains a `:` (splitting
    a module from a qualname), MODULE if it is a bare dotted-identifier
    chain, else PATH as the catch-all for anything unparseable as either
    -- so a mismatched operand is refused BY NAME rather than silently
    fed into a rewriter that guesses at its shape."""
    if not text or "/" in text or "\\" in text:
        return OperandKind.PATH
    if ":" in text:
        return OperandKind.SYMBOL
    if _is_dotted_identifier_chain(text):
        return OperandKind.MODULE
    return OperandKind.PATH


# frob:doc docs/commands/refactor.md#parse_symbol_operand
# frob:tests tests/test_refactor.py::TestOperands.test_parse_symbol_operand_refuses_module_shaped  # noqa: E501
def parse_symbol_operand(text: str) -> Result[SymbolRef, OperandError]:
    """Parse `text` as a SYMBOL operand (`module:qualname`), refusing
    `Err(WrongOperandKind)` for anything MODULE- or PATH-shaped -- the
    `move`/`rename` verbs' own operand gate."""
    if classify_operand(text) != OperandKind.SYMBOL:
        return Err(OperandError.WrongOperandKind)
    module, _, qualname = text.partition(":")
    if not module or not qualname:
        return Err(OperandError.WrongOperandKind)
    return Ok(SymbolRef(module=module, qualname=qualname))


# frob:doc docs/commands/refactor.md#parse_module_operand
# frob:tests tests/test_refactor.py::TestOperands.test_parse_module_operand_refuses_symbol_shaped  # noqa: E501
def parse_module_operand(text: str) -> Result[ModuleRef, OperandError]:
    """Parse `text` as a MODULE operand (a bare dotted path, no `:`),
    refusing `Err(WrongOperandKind)` for anything SYMBOL- or PATH-shaped
    -- `move-module`'s own operand gate, the mirror of
    `parse_symbol_operand`."""
    if classify_operand(text) != OperandKind.MODULE:
        return Err(OperandError.WrongOperandKind)
    return Ok(ModuleRef(module=text))


# frob:doc docs/commands/refactor.md#validate_module_destination
# frob:tests tests/test_refactor.py::TestOperands.test_validate_destination_refuses_non_identifier_segment  # noqa: E501
# frob:tests tests/test_refactor.py::TestOperands.test_validate_destination_refuses_existing_module  # noqa: E501
def validate_module_destination(
    repo_root: Path, ref: ModuleRef, *, allow_existing: bool = False
) -> Result[Path, OperandError]:
    """Validate `ref` as a legal Python module DESTINATION before any
    file is written: every `.`-separated segment must be a valid Python
    identifier, the mapped path must land inside the repo's declared
    source root (`src/` when present, else `repo_root`) and end in
    `.py`, and -- absent `allow_existing=True` -- the destination must
    not already exist. Returns the destination `Path` on success; every
    failure is a typed `OperandError`, never a partial write (this is a
    pure check, nothing here touches the filesystem beyond `is_file`)."""
    from frob.refactor._resolve import module_to_path

    if not _is_dotted_identifier_chain(ref.module):
        return Err(OperandError.InvalidDestination)

    dest_path = module_to_path(repo_root, ref.module)
    if dest_path.suffix != ".py":
        return Err(OperandError.InvalidDestination)

    src_root = repo_root / "src"
    base = src_root if src_root.is_dir() else repo_root
    try:
        dest_path.relative_to(base)
    except ValueError:
        return Err(OperandError.InvalidDestination)

    if dest_path.is_file() and not allow_existing:
        return Err(OperandError.DestinationExists)
    return Ok(dest_path)

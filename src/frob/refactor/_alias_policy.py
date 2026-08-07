"""Alias-conflict policy (T-1202): what happens when a move/rename's
DESTINATION namespace already binds a distinct symbol under the name
being moved there (docs/design/refactor-verb.md's "Alias-conflict
policy" section) -- a different collision kind than the import-site name
collision `frob.refactor._scan.scan_references` already resolves on its
own (that one auto-aliases the IMPORTING call site; this one is about
the symbol already living at the destination).

Two policies, selected by `--alias-conflict {error,rename-dest}`
(default `error`, matching `_transaction._destination_collision`'s
pre-T-1202 behavior exactly -- a destination collision is a hard refusal
unless the caller explicitly opts into the auto-rename):

- `error` (default): `_transaction.build_plan` returns
  `Err(DestinationCollision)` before any file is written -- unchanged
  from T-1197.
- `rename-dest`: the EXISTING colliding symbol is renamed out of the way
  (an in-place identifier substitution on its own def/class line, plus
  every call site `scan_references` finds for it, mirroring the move
  engine's own reference-rewrite machinery rather than reimplementing
  it) so the incoming move can land under the name it asked for. Every
  auto-generated rename is recorded as an `AliasRecord` so the disclosed
  report names it in its own labeled section, same as an import-site
  alias (epic acceptance [2]).
"""

from __future__ import annotations

import re
from pathlib import Path

from frob.refactor._models import AliasRecord, ResolvedSymbol, RewriteOp, SymbolRef
from frob.refactor._scan import scan_references

__all__ = ["resolve_rename_dest_collision"]

#: Suffix appended to an existing colliding destination symbol's own leaf
#: name when `--alias-conflict rename-dest` renames it out of the way --
#: mirrors `_handle_from_import`'s own `_refactored` suffix convention
#: for an import-site alias (`tests/test_refactor.py::TestScanReferences.
#: test_auto_alias_on_call_site_name_collision`), so every auto-generated
#: name in this package follows one recognizable pattern.
_RENAME_DEST_SUFFIX = "_existing"


def _rename_def_identifier(def_line: str, old_leaf: str, new_leaf: str) -> str:
    """Substitute `old_leaf` for `new_leaf` right after the `def`/`class`
    keyword on `def_line`, leaving everything else (decorators processed
    on their own lines, return-type annotations, docstrings) untouched --
    a plain identifier rename, not a span move, since the existing
    symbol stays exactly where it already lives."""
    pattern = re.compile(
        r"^(\s*(?:async\s+)?(?:def|class)\s+)" + re.escape(old_leaf) + r"\b"
    )
    return pattern.sub(rf"\g<1>{new_leaf}", def_line, count=1)


# frob:doc docs/commands/refactor.md#resolve_rename_dest_collision
# frob:tests tests/test_refactor.py::TestAliasPolicy.test_rename_dest_renames_existing_symbol_and_its_callers  # noqa: E501
def resolve_rename_dest_collision(
    repo_root: Path, existing: ResolvedSymbol, requested_leaf: str
) -> tuple[RewriteOp, list[RewriteOp], AliasRecord]:
    """`--alias-conflict rename-dest`'s own resolution: rename the
    EXISTING symbol occupying `requested_leaf` at the destination module
    to a disambiguated name (`_RENAME_DEST_SUFFIX`), rewrite every call
    site `scan_references` finds for it (reusing the move engine's own
    reference-rewrite pass rather than a second implementation), and
    return `(own_rename_op, caller_ops, alias_record)` for `build_plan`
    to fold into `reference_ops`/`aliases` alongside the incoming move's
    own ops."""
    old_leaf = existing.ref.qualname.split(".")[-1]
    new_leaf = f"{old_leaf}{_RENAME_DEST_SUFFIX}"
    new_ref = SymbolRef(module=existing.ref.module, qualname=new_leaf)

    lines = Path(existing.file_path).read_text(encoding="utf-8").splitlines()
    def_line = lines[existing.start_line - 1]
    own_rename_op = RewriteOp(
        file_path=existing.file_path,
        start_line=existing.start_line,
        end_line=existing.start_line,
        old_text=def_line,
        new_text=_rename_def_identifier(def_line, old_leaf, new_leaf),
        reason=(
            f"rename-dest policy: destination-namespace collision on "
            f"{requested_leaf!r} resolved by renaming the existing symbol to "
            f"{new_ref.dotted}"
        ),
    )
    caller_ops, _aliases, _unresolved = scan_references(
        repo_root, existing, new_ref, alias_conflict="error"
    )
    alias = AliasRecord(
        file_path=existing.file_path,
        original_name=old_leaf,
        alias_name=new_leaf,
        reason=(
            "destination-namespace collision resolved via --alias-conflict rename-dest"
        ),
    )
    return own_rename_op, caller_ops, alias

"""Registry/evidence repointer (T-1200): the three moving-symbol
reference kinds the directive carrier (T-1199, `frob.refactor._directives`)
cannot reach, because none of them is a `frob:*` DSL edge
(docs/design/refactor-verb.md's reference-kind inventory):

1. The PII012 manually-reviewed (file, identifier-text) allowlist
   (`_PII012_REVIEWED_NON_PII`, `frob.gates._pii_structural._keywords`) --
   a plain Python frozenset literal keyed on OTHER modules' paths, not a
   DSL directive at all (`scan_pii_allowlist_carrier`).
2. A `docs/design/registry/*.yaml` entry whose `cross_refs` embeds a
   literal `path::qualname` string for a moving symbol -- YAML data, not
   a `frob:enforces` edge (`scan_registry_citations`).
3. A closed ticket's Evidence section in `tickets.md`/`tickets-archive.md`
   citing a `path::Class.method` symref or a pytest `path::Class::method`
   node id for a moving symbol -- ledger prose, not a DSL edge
   (`scan_evidence_citations`).

Each function mirrors `_directives.scan_directive_carriers`'s own shape
(`(repo_root, resolved, destination) -> (ops, unresolved)`, text-level
literal-substring rewrite) so `_transaction.build_plan` can fold their
output into `RefactorPlan.reference_ops` exactly like the directive
carrier's own ops, rather than needing a second code path.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from pathlib import Path

from frob.logging import get_logger
from frob.refactor._models import ResolvedSymbol, RewriteOp, SymbolRef

_log = get_logger(__name__)

__all__ = [
    "scan_evidence_citations",
    "scan_pii_allowlist_carrier",
    "scan_registry_citations",
]

#: Fixed home of the PII012 manually-reviewed allowlist
#: (`_keywords.py`'s own module docstring: "a (file, identifier-text)
#: allowlist keyed by OTHER modules' paths"). A single well-known path
#: rather than a repo-wide scan -- there is exactly one such table in the
#: codebase today.
_PII012_ALLOWLIST_FILE = "src/frob/gates/_pii_structural/_keywords.py"

#: The ledger files a closed ticket's Evidence section can live in --
#: both need scanning, per the ticket's own plan note ("Both files, not
#: just the live ledger").
_LEDGER_FILES = ("tickets.md", "tickets-archive.md")

#: Directories a repo-wide yaml/text scan below should never walk --
#: matches `frob.refactor._scan._SKIP_DIRS`'s own exclusion set (kept as
#: a private copy here rather than importing a private name across
#: modules).
_SKIP_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "build",
        "dist",
        "node_modules",
        ".frob",
    }
)


# frob:waive EXHAUST003 reason="T-1636: leaked Unknown traces to path.as_posix(), a \
# Path method the resolver's curated table does not cover (never raises); the one real \
# raise path (path.relative_to outside repo_root) is caught below"
def _display_path(repo_root: Path, path: Path) -> str:
    """Repo-relative POSIX path when possible, else the path as given --
    mirrors `frob.refactor._directives._display_path` exactly (same
    convention every symref in this package is built from; a mismatched
    convention here would silently never match a real citation)."""
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _old_and_dest_rel(
    repo_root: Path, resolved: ResolvedSymbol, destination: SymbolRef
) -> tuple[str, str]:
    """The old and new repo-relative file paths for `resolved`'s move to
    `destination` -- the shared computation every scan below needs
    before it can build its own rewrite map."""
    from frob.refactor._resolve import module_to_path

    old_rel = _display_path(repo_root, Path(resolved.file_path))
    dest_rel = _display_path(repo_root, module_to_path(repo_root, destination.module))
    return old_rel, dest_rel


# frob:doc docs/commands/refactor.md#scan_pii_allowlist_carrier
# frob:tests tests/test_refactor.py::TestRepointer.test_pii_allowlist_entry_rekeyed_on_move  # noqa: E501
def scan_pii_allowlist_carrier(
    repo_root: Path, resolved: ResolvedSymbol, destination: SymbolRef
) -> tuple[list[RewriteOp], list[str]]:
    """PII012 allowlist carrier: any `_PII012_REVIEWED_NON_PII` entry
    keyed `(old_rel_path, token)` where `old_rel_path` matches the moving
    symbol's OLD file and `token` matches its own leaf name gets re-keyed
    to `(new_rel_path, token)` -- the token half is never touched (the
    ticket's own acceptance: "no new PII012 finding fires ... for that
    token", not a different one). A no-op (empty ops, empty unresolved)
    when the allowlist file does not exist or holds no matching entry --
    both the normal, non-error case."""
    allowlist_path = repo_root / _PII012_ALLOWLIST_FILE
    if not allowlist_path.is_file():
        return [], []

    old_rel, dest_rel = _old_and_dest_rel(repo_root, resolved, destination)
    if old_rel == dest_rel:
        # Rename-in-place: the file half of any entry is unaffected.
        return [], []
    leaf = resolved.ref.qualname.split(".")[-1]

    lines = allowlist_path.read_text(encoding="utf-8").splitlines()
    old_entry_text = f'("{old_rel}", "{leaf}")'
    new_entry_text = f'("{dest_rel}", "{leaf}")'

    ops: list[RewriteOp] = []
    for lineno, line in enumerate(lines, start=1):
        if old_entry_text not in line:
            continue
        ops.append(
            RewriteOp(
                file_path=str(allowlist_path),
                start_line=lineno,
                end_line=lineno,
                old_text=line,
                new_text=line.replace(old_entry_text, new_entry_text),
                reason=(
                    f"carry PII012 allowlist entry {old_entry_text} -> {new_entry_text}"
                ),
            )
        )
    return ops, []


# frob:doc docs/commands/refactor.md#scan_registry_citations
# frob:tests tests/test_refactor.py::TestRepointer.test_registry_cross_ref_rewritten  # noqa: E501
def scan_registry_citations(
    repo_root: Path, resolved: ResolvedSymbol, destination: SymbolRef
) -> tuple[list[RewriteOp], list[str]]:
    """`docs/design/registry/*.yaml` carrier: any line whose literal text
    contains the moving symbol's old `path::qualname` symref -- a
    `cross_refs` entry is the observed case, but this matches the literal
    substring wherever it appears in a registry yaml, not a specific key,
    since a citation is free-text YAML, not a parsed schema field this
    package owns. A registry with no such citation (the common case --
    most `disposition` values cite a bare gate id, never a symref) yields
    empty ops, not an error."""
    registry_dir = repo_root / "docs" / "design" / "registry"
    if not registry_dir.is_dir():
        return [], []

    old_rel, dest_rel = _old_and_dest_rel(repo_root, resolved, destination)
    old_symref = f"{old_rel}::{resolved.ref.qualname}"
    new_symref = f"{dest_rel}::{destination.qualname}"
    if old_symref == new_symref:
        return [], []

    ops: list[RewriteOp] = []
    unresolved: list[str] = []
    for yaml_path in sorted(registry_dir.glob("*.yaml")):
        try:
            text = yaml_path.read_text(encoding="utf-8")
        except OSError as exc:
            unresolved.append(f"{yaml_path}: unreadable ({exc})")
            continue
        if old_symref not in text:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if old_symref not in line:
                continue
            ops.append(
                RewriteOp(
                    file_path=str(yaml_path),
                    start_line=lineno,
                    end_line=lineno,
                    old_text=line,
                    new_text=line.replace(old_symref, new_symref),
                    reason=f"carry registry citation {old_symref} -> {new_symref}",
                )
            )
    return ops, unresolved


def _pytest_node_id(rel_path: str, qualname: str) -> str | None:
    """The pytest `path::Class::method` node-id form for a `Class.method`
    qualname, or `None` for a bare top-level qualname (no `.` -- a plain
    function's node id is already `path::qualname`, identical to the DSL
    symref form, so no second variant is needed)."""
    if "." not in qualname:
        return None
    return f"{rel_path}::{qualname.replace('.', '::')}"


# frob:doc docs/commands/refactor.md#scan_evidence_citations
# frob:tests tests/test_refactor.py::TestRepointer.test_ticket_evidence_symref_rewritten  # noqa: E501
def scan_evidence_citations(
    repo_root: Path, resolved: ResolvedSymbol, destination: SymbolRef
) -> tuple[list[RewriteOp], list[str]]:
    """`tickets.md`/`tickets-archive.md` carrier: any line citing the
    moving symbol's old `path::Class.method` symref OR its pytest
    `path::Class::method` node-id form gets rewritten to the destination's
    equivalent -- both files, per the ticket's own plan note, since a
    closed ticket's Evidence lives in either one. A ledger with no
    matching citation (evidence overwhelmingly cites TEST node ids for
    unrelated test functions, not a moving PRODUCTION symbol) yields
    empty ops, not an error."""
    old_rel, dest_rel = _old_and_dest_rel(repo_root, resolved, destination)
    old_symref = f"{old_rel}::{resolved.ref.qualname}"
    new_symref = f"{dest_rel}::{destination.qualname}"
    old_node_id = _pytest_node_id(old_rel, resolved.ref.qualname)
    new_node_id = _pytest_node_id(dest_rel, destination.qualname)

    rewrite_map: dict[str, str] = {}
    if old_symref != new_symref:
        rewrite_map[old_symref] = new_symref
    if (
        old_node_id is not None
        and new_node_id is not None
        and old_node_id != new_symref
    ):
        rewrite_map[old_node_id] = new_node_id
    if not rewrite_map:
        return [], []

    ops: list[RewriteOp] = []
    for rel_ledger in _LEDGER_FILES:
        ledger_path = repo_root / rel_ledger
        if not ledger_path.is_file():
            continue
        lines = ledger_path.read_text(encoding="utf-8").splitlines()
        for lineno, line in enumerate(lines, start=1):
            hit = next((old for old in rewrite_map if old in line), None)
            if hit is None:
                continue
            new_line = line.replace(hit, rewrite_map[hit])
            ops.append(
                RewriteOp(
                    file_path=str(ledger_path),
                    start_line=lineno,
                    end_line=lineno,
                    old_text=line,
                    new_text=new_line,
                    reason=(
                        f"carry ticket evidence citation {hit} -> {rewrite_map[hit]}"
                    ),
                )
            )
    return ops, []

# frob:ticket T-4657
"""Unit tests for the typed ledger store API seam (`frob.tickets._store_api`).

T-4657 (kernel decoupling, LEDGER story): today ticket data is reached a
dozen different ways across `src/frob/tickets/*.py` and
`src/frob/app/ticket_runner/*.py` -- there is no single seam. This suite
proves the new seam exists, that it hands back typani `Result` values
(never raises) on the fallible paths, and ratchets the set of modules
allowed to open a `tickets/**/ticket.md` path directly so the seam cannot
silently regrow new bypasses.
"""

from __future__ import annotations

import ast
from datetime import date
from pathlib import Path

# frob:tests src/frob/tickets/_store_api.py::get_ticket kind="unit"
# frob:tests src/frob/tickets/_store_api.py::put_ticket kind="unit"
# frob:tests src/frob/tickets/_store_api.py::list_tickets kind="unit"
# frob:tests src/frob/tickets/_store_api.py::get_archived_ticket kind="unit"
# frob:tests src/frob/tickets/_store_api.py::put_archived_ticket kind="unit"
# frob:tests src/frob/tickets/_store_api.py::list_archived_tickets kind="unit"
from frob.tickets import _store_api
from frob.tickets._models import Origin, Ticket, TicketError, TicketKind, TicketState

# T-4657: the fixed set of modules with pre-existing, grandfathered direct
# `tickets/**/ticket.md` access as measured on dev at the time this leaf was
# filed. `_store.py`/`_store_migrate.py` are the mode-dispatched
# implementation `_store_api.py` wraps; the rest are historical readers this
# leaf's scope (`src/frob/tickets/_store_api.py` and this test only) does not
# migrate -- see docs/modules/tickets-data-storage.md's "Store API seam"
# section. New sites outside this allowlist are refused: the point of this
# test is that the allowlist can only shrink from here, never silently grow.
_GRANDFATHERED_DIRECT_ACCESS = frozenset(
    {
        "src/frob/tickets/_store.py",
        "src/frob/tickets/_store_migrate.py",
        "src/frob/tickets/_store_api.py",
        "src/frob/gates/_bug_repro.py",
        "src/frob/refactor/_module_prose.py",
        "src/frob/tickets/_land_squash.py",
        "src/frob/_cli_parsers/_ticket/_progress.py",
        "src/frob/_cli_parsers/_ticket/_metadata.py",
        "src/frob/_cli_parsers/_ticket/_closeout.py",
        "src/frob/gates/_docptr.py",
        "src/frob/gates/_fix_engine.py",
        "src/frob/gates/_empty_diff_close.py",
        "src/frob/gates/_tickets_gate.py",
        "src/frob/gates/_mutation_evidence.py",
        "src/frob/gates/_refs.py",
        "src/frob/gates/_gate_cache.py",
        "src/frob/gates/_waive.py",
        "src/frob/gates/__init__.py",
        "src/frob/refactor/_repointer.py",
        "src/frob/check/_python.py",
        "src/frob/tickets/_flow.py",
        "src/frob/tickets/_scope.py",
        "src/frob/tickets/_renumber_v2.py",
        "src/frob/app/ticket_runner/_land_cmd.py",
        "src/frob/app/ticket_runner/_ledger_mirror.py",
        "src/frob/refactor/_verify.py",
        "src/frob/tickets/_archive.py",
        "src/frob/tickets/_models.py",
        "src/frob/tickets/_reconcile.py",
        "src/frob/tickets/_land.py",
        "src/frob/tickets/_setters.py",
        "src/frob/tickets/_land_git_ops.py",
        "src/frob/tickets/_reporting.py",
        "src/frob/tickets/_unlanded.py",
        "src/frob/app/config.py",
        "src/frob/tickets/_leases.py",
        "src/frob/app/ticket_runner/_close_cmd.py",
        "src/frob/tickets/_worktree_sweep.py",
        "src/frob/app/ticket_runner/_rapid_sweep.py",
        "src/frob/refactor/_models.py",
    }
)

_DIRECT_ACCESS_CALL_NAMES = {"open"}
_DIRECT_ACCESS_ATTRS = {"read_text", "write_text", "read_bytes", "write_bytes"}


def _repo_root() -> Path:
    """The frob checkout root, three parents up from this test file."""
    return Path(__file__).resolve().parents[2]


def _mentions_ticket_md_literal(node: ast.Call) -> bool:
    """True if a call node has a string argument containing `ticket.md`."""
    for arg in list(node.args) + [kw.value for kw in node.keywords]:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            if "ticket.md" in arg.value:
                return True
    return False


def _direct_ticket_md_access_sites(py_file: Path) -> list[str]:
    """Call sites in `py_file` that look like a raw open/read/write of a
    `ticket.md` path -- either a literal `"...ticket.md"` argument to
    `open()`, or a `.read_text()`/`.write_text()`/`.read_bytes()`/
    `.write_bytes()` call on an expression whose source text mentions
    `ticket.md` or `ticket_path`/`ticket_md` (the common local-variable
    names for such a path in this codebase)."""
    try:
        source = py_file.read_text(encoding="utf-8")
    except OSError:
        return []
    tree = ast.parse(source, filename=str(py_file))
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id in _DIRECT_ACCESS_CALL_NAMES:
            if _mentions_ticket_md_literal(node):
                hits.append(f"{py_file}:{node.lineno}")
        elif isinstance(func, ast.Attribute) and func.attr in _DIRECT_ACCESS_ATTRS:
            target = func.value
            target_src = ast.dump(target)
            if "ticket_md" in target_src or "ticket_path" in target_src:
                hits.append(f"{py_file}:{node.lineno}")
    return hits


def test_no_module_opens_ticket_md_directly() -> None:
    """POSITIVE CONTROL (T-4657): fails on dev today because
    `frob.tickets._store_api` does not exist yet; after this leaf the
    import succeeds AND no module outside the grandfathered allowlist
    performs a raw `ticket.md` read/write. A module planted outside the
    allowlist with a direct `open("...ticket.md")` call would be caught by
    the AST scan below, proving the check is not a silent no-op."""
    root = _repo_root()
    src_root = root / "src" / "frob"
    violations: list[str] = []
    for py_file in sorted(src_root.rglob("*.py")):
        rel = py_file.relative_to(root).as_posix()
        if rel in _GRANDFATHERED_DIRECT_ACCESS:
            continue
        violations.extend(_direct_ticket_md_access_sites(py_file))
    assert violations == [], (
        "new direct tickets/**/ticket.md access outside the _store_api "
        f"seam and the grandfathered allowlist: {violations}"
    )


def test_ast_scan_catches_a_planted_violation(tmp_path: Path) -> None:
    """Companion control: the AST scan in `_direct_ticket_md_access_sites`
    must actually fire on a real violation shape, not just always return
    empty -- guards against the previous test passing for the wrong
    reason (a scan that never matches anything)."""
    planted = tmp_path / "planted_offender.py"
    planted.write_text(
        'def read_it(path):\n    with open("tickets/T-0001/ticket.md") as f:\n'
        "        return f.read()\n",
        encoding="utf-8",
    )
    assert _direct_ticket_md_access_sites(planted) != []


def _ticket(ticket_id: str = "T-0001", title: str = "Sample ticket") -> Ticket:
    """Minimal valid `Ticket` fixture for store-api round-trip tests."""
    return Ticket(
        id=ticket_id,
        title=title,
        state=TicketState.QUEUED,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        blocked_by=(),
        parent=None,
        scope=(),
        evidence=(),
        attachments=(),
        body="## Description\nsomething\n",
    )


# frob:tests src/frob/tickets/_store_api.py::get_ticket
def test_missing_ticket_is_a_result_error(tmp_path: Path) -> None:
    """`get_ticket` on an id that does not exist returns an `Err`, never
    raises -- the fallible-path contract this seam exists to enforce."""
    (tmp_path / "tickets").mkdir()
    result = _store_api.get_ticket(tmp_path, "T-9999")
    assert result.is_err
    assert result.danger_err == TicketError.NotFound


def test_put_then_get_round_trips(tmp_path: Path) -> None:
    """A ticket written via `put_ticket` is readable back via `get_ticket`
    with the same id and title, proving the seam's write and read sides
    agree with each other."""
    (tmp_path / "tickets").mkdir()
    ticket = _ticket()
    written = _store_api.put_ticket(tmp_path, ticket)
    assert written.is_ok

    fetched = _store_api.get_ticket(tmp_path, ticket.id)
    assert fetched.is_ok
    assert fetched.danger_ok.id == ticket.id
    assert fetched.danger_ok.title == ticket.title

    listed = _store_api.list_tickets(tmp_path)
    assert listed.is_ok
    assert ticket.id in listed.danger_ok


def test_archived_put_then_get_round_trips(tmp_path: Path) -> None:
    """The archive half of the seam agrees with itself the same way the
    live half does: a ticket written via `put_archived_ticket` comes back
    through `get_archived_ticket` and appears in `list_archived_tickets`,
    and a missing archived id is an `Err`, never a raise."""
    (tmp_path / "tickets").mkdir()
    missing = _store_api.get_archived_ticket(tmp_path, "T-9999")
    assert missing.is_err

    ticket = _ticket()
    written = _store_api.put_archived_ticket(tmp_path, ticket)
    assert written.is_ok

    fetched = _store_api.get_archived_ticket(tmp_path, ticket.id)
    assert fetched.is_ok
    assert fetched.danger_ok.id == ticket.id

    listed = _store_api.list_archived_tickets(tmp_path)
    assert listed.is_ok
    assert ticket.id in listed.danger_ok


def test_docs_name_store_api_as_the_entry_point() -> None:
    """docs/modules/tickets-data-storage.md must name `_store_api` as the
    single entry point in the same change that introduces it (acceptance
    criterion [3])."""
    root = _repo_root()
    doc = root / "docs" / "modules" / "tickets-data-storage.md"
    text = doc.read_text(encoding="utf-8")
    assert "_store_api" in text
    assert "single entry point" in text

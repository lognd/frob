"""T-3110: a realistic call-site-shape corpus for `frob refactor`'s
verbs (`split`, `move`, `move-module`, `rename`), covering the exact
shapes that produced T-3066/T-3105/T-3109 -- shapes NONE of
`test_refactor.py`'s existing small synthetic fixtures combine into one
target. The verb had never been exercised against a realistic,
heavily-imported module before those three defects; this module is the
regression guard against a fourth.

Every shape lives in ONE fixture repo built by `_corpus_repo`, exercised
by ONE `run_split` (mirroring the real T-3086 `gates._models` extraction
shape: several symbols out of one heavily-imported module) so the corpus
proves the shapes interact correctly together, not just in isolation.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

from frob.refactor import RefactorKind, SymbolRef, run_split
from frob.tickets import TicketKind, TicketSpec, new_ticket
from frob.tickets._models import Origin


def _repo(tmp_path: Path) -> Path:
    """A git-initialized repo root -- same fixture shape as
    `test_refactor.py::_repo` (T-1197's established convention); not
    imported cross-file per that module's own DUP001 waiver precedent."""
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    return tmp_path


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _commit_all(root: Path, subject: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", subject], cwd=root, check=True)


def _assert_all_py_files_parse(root: Path) -> None:
    """Every tracked `.py` file under `root` is still valid Python --
    the minimum "importable" bar T-3105 failed while reporting
    `success=True`. Deliberately checks the WHOLE tree, not just the
    plan's own `touched_files` list (which is exactly the scope
    `verify_import_resolution` limits itself to) -- a corpus assertion
    that only re-checked touched files would not have caught T-3105's
    130 wrongly-rewritten-but-NOT-import-checked files any better than
    the shipped code did."""
    broken: list[str] = []
    for py_file in sorted(root.rglob("*.py")):
        if ".git" in py_file.parts:
            continue
        try:
            ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except SyntaxError as exc:
            broken.append(f"{py_file}: {exc}")
    assert broken == [], broken


def _corpus_repo(tmp_path: Path) -> Path:
    """One fixture repo combining every call-site shape T-3066/T-3105/
    T-3109 needed real scale to surface: a function-local import, a
    `TYPE_CHECKING`-guarded import, a `try`/`except ImportError`-guarded
    import, an import nested several blocks deep, a from-import line
    naming BOTH a moved and an untouched symbol, a re-export line naming
    many symbols (the `gates/__init__.py` shape T-3105 broke), a
    relative import of the source module, and an aliased import --
    plus a `tickets/<id>/ticket.md` structured evidence citation (the
    non-Python carrier surface these verbs are specifically supposed to
    handle, T-1885's own repro shape).

    `pkg.mod` defines two symbols the split moves (`moved_a`, `moved_b`)
    and one it leaves behind (`kept_c`), mirroring T-3086's real target
    (`gates._models`: several universal value types moved, the rest of
    the module untouched)."""
    root = _repo(tmp_path)
    _write(root, "src/pkg/__init__.py", "")
    _write(
        root,
        "src/pkg/mod.py",
        "def moved_a():\n"
        "    return 'a'\n"
        "\n\n"
        "def moved_b():\n"
        "    return 'b'\n"
        "\n\n"
        "def kept_c():\n"
        "    return 'c'\n",
    )
    # Re-export line naming many symbols -- the `gates/__init__.py`
    # shape T-3105 broke by repointing the WHOLE line, including
    # `kept_c`, at the destination module.
    _write(
        root,
        "src/pkg/reexport.py",
        "from pkg.mod import moved_a, moved_b, kept_c\n\n"
        "def use():\n    return moved_a() + moved_b() + kept_c()\n",
    )
    # Function-local import (T-3066/T-3109 shape).
    _write(
        root,
        "src/pkg/caller_local.py",
        "def use():\n    from pkg.mod import moved_a\n    return moved_a()\n",
    )
    # `TYPE_CHECKING`-guarded import (T-3066 shape).
    _write(
        root,
        "src/pkg/caller_type_checking.py",
        "import typing\n\n"
        "if typing.TYPE_CHECKING:\n"
        "    from pkg.mod import moved_a\n\n"
        "def use() -> \"moved_a\":\n    pass\n",
    )
    # `try`/`except ImportError`-guarded import (T-3066 shape).
    _write(
        root,
        "src/pkg/caller_try_except.py",
        "try:\n"
        "    from pkg.mod import moved_a\n"
        "except ImportError:\n"
        "    moved_a = None\n\n"
        "def use():\n    return moved_a\n",
    )
    # Import nested several blocks deep (T-3109's indentation shape, at
    # a deeper level than the single-level repro in test_refactor.py).
    _write(
        root,
        "src/pkg/caller_nested.py",
        "def outer():\n"
        "    if True:\n"
        "        for _ in range(1):\n"
        "            from pkg.mod import moved_b\n"
        "            return moved_b()\n"
        "    return None\n",
    )
    # From-import line naming BOTH a moved and an untouched symbol
    # (T-3105 shape).
    _write(
        root,
        "src/pkg/caller_mixed.py",
        "from pkg.mod import moved_a, kept_c\n\n"
        "def use():\n    return moved_a() + kept_c()\n",
    )
    # Relative import of the source module -- must keep working via the
    # split's re-export shim without any special-casing (a relative
    # `from .mod import ...` is not matched by `old_ref.module`'s
    # absolute dotted path, so it is never rewritten; the shim in
    # `pkg/mod.py` itself is what keeps it valid).
    _write(
        root,
        "src/pkg/caller_relative.py",
        "from .mod import moved_a\n\ndef use():\n    return moved_a()\n",
    )
    # Aliased import.
    _write(
        root,
        "src/pkg/caller_aliased.py",
        "from pkg.mod import moved_a as ma\n\ndef use():\n    return ma()\n",
    )

    # Non-Python reference surface: a real ticket with a structured
    # evidence citation naming the moving symbol's OLD node id (T-1885's
    # own repro shape) -- the split must neither crash on it nor lose
    # the citation.
    created = new_ticket(
        root,
        TicketSpec(
            title="t3110 corpus evidence carrier",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            scope=("src/pkg/mod.py",),
            evidence=("src/pkg/mod.py::moved_a",),
        ),
    )
    assert created.is_ok, created.err

    _commit_all(root, "initial")
    return root


class TestRefactorCorpus:
    def test_split_moves_symbols_across_every_call_site_shape(self, tmp_path):
        # frob:tests \
        # tests/test_refactor_corpus.py::TestRefactorCorpus.test_split_moves_symbols_a\
        # cross_every_call_site_shape
        root = _corpus_repo(tmp_path)

        result = run_split(
            root,
            source_module="pkg.mod",
            symbols=["moved_a", "moved_b"],
            destination_module="pkg.newmod",
            chunk_size=5,
            run_pytest_collect=False,
            run_check_delta=False,
        )
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.success is True, report
        assert all(c.rolled_back is False for c in report.chunks), report.chunks
        assert report.moved_symbols == ("moved_a", "moved_b")

        # The minimum bar T-3105 failed while reporting success=True:
        # the WHOLE tree must still parse, not just the files the plan
        # itself touched.
        _assert_all_py_files_parse(root)

        # The destination module actually defines what moved.
        newmod_text = (root / "src/pkg/newmod.py").read_text(encoding="utf-8")
        assert "def moved_a" in newmod_text
        assert "def moved_b" in newmod_text

        # `kept_c` never moved -- neither definition nor any call site
        # was repointed at the destination.
        mod_text = (root / "src/pkg/mod.py").read_text(encoding="utf-8")
        assert "def kept_c" in mod_text
        assert "kept_c" not in newmod_text

        # Re-export line: kept unmodified (T-3105) -- `kept_c` must
        # never be dragged into a `pkg.newmod` import.
        reexport_text = (root / "src/pkg/reexport.py").read_text(encoding="utf-8")
        assert reexport_text.startswith("from pkg.mod import moved_a, moved_b, kept_c")

        # Function-local import: rewritten AND still indented (T-3109).
        local_text = (root / "src/pkg/caller_local.py").read_text(encoding="utf-8")
        assert "    from pkg.newmod import moved_a" in local_text
        assert "    return moved_a()" in local_text

        # TYPE_CHECKING-guarded import: rewritten, still indented under
        # the `if` block, and does not false-refuse (T-3066).
        tc_text = (root / "src/pkg/caller_type_checking.py").read_text(
            encoding="utf-8"
        )
        assert "    from pkg.newmod import moved_a" in tc_text

        # try/except-guarded import: rewritten, still indented under
        # `try:`, and does not false-refuse (T-3066).
        try_text = (root / "src/pkg/caller_try_except.py").read_text(
            encoding="utf-8"
        )
        assert "    from pkg.newmod import moved_a" in try_text

        # Deeply-nested import (function -> if -> for): rewritten at its
        # own (deeper) indent depth, not module scope (T-3109).
        nested_text = (root / "src/pkg/caller_nested.py").read_text(
            encoding="utf-8"
        )
        assert "            from pkg.newmod import moved_b" in nested_text

        # Mixed moved/untouched import line: left alone entirely
        # (T-3105) -- `kept_c` is not defined at the destination.
        mixed_text = (root / "src/pkg/caller_mixed.py").read_text(encoding="utf-8")
        assert mixed_text.startswith("from pkg.mod import moved_a, kept_c")

        # Relative import: never touched by the scan (it matches on
        # `old_ref.module`'s absolute dotted path only), but stays valid
        # because the re-export shim keeps `pkg.mod` re-exporting
        # `moved_a`.
        relative_text = (root / "src/pkg/caller_relative.py").read_text(
            encoding="utf-8"
        )
        assert relative_text.startswith("from .mod import moved_a")

        # Aliased import: rewritten at the destination -- the mechanical
        # rewrite drops the local alias and renames call sites to the
        # canonical destination name instead of trying to preserve `as
        # ma` (matching `_handle_from_import`'s documented `bound_as !=
        # new_name` rename-usages path).
        aliased_text = (root / "src/pkg/caller_aliased.py").read_text(
            encoding="utf-8"
        )
        assert "from pkg.newmod import moved_a" in aliased_text
        assert "return moved_a()" in aliased_text

        # Non-Python carrier: the ticket.md evidence citation for the
        # moved symbol is disclosed as skipped by import_resolution
        # (T-1885), not silently dropped or mis-parsed as Python.
        all_outcomes = [o for c in report.chunks for o in c.verify_outcomes]
        import_outcome = next(o for o in all_outcomes if o.name == "import_resolution")
        assert import_outcome.passed is True
        assert any(
            str(root / "tickets") in skipped_path
            for skipped_path in import_outcome.skipped
        ), import_outcome.skipped

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert status.strip() == ""

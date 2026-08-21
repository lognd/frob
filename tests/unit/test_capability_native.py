"""T-1221: golden tests for `frob_core.scan_python_capabilities`, the
native rust capability-scan resolver -- byte-identical candidate parity
against `frob.vet._capability_python._python_resolved_candidates` and
`frob.vet._capability_core._non_executable_byte_spans`, plus this
kernel's own UNRESOLVED requirement (a dynamic-dispatch call site the
resolver can see but cannot identify must be its own loud outcome, never
silently folded into "no capability")."""

from __future__ import annotations

from pathlib import Path

import frob_core

from frob.vet import _capability_core as cc
from frob.vet import _capability_python as cp
from frob.vet._capability_scan import scan_file_capabilities


def _write(source: bytes, tmp_path: Path) -> Path:
    """Write `source` to a fresh `.py` file under `tmp_path` and return it
    -- both the native kernel and the Python resolver read from disk."""
    path = tmp_path / "sample.py"
    path.write_bytes(source)
    return path


class TestScanPythonCapabilitiesParity:
    """`frob_core.scan_python_capabilities`'s `candidates`/`spans` vs the
    existing Python resolver (`_capability_python`/`_capability_core`),
    across representative shapes plus this repo's own source."""

    def test_import_alias_and_scope_shadowing(self, tmp_path: Path) -> None:
        # frob:tests frob-core/src/capability_python.rs::scan_python_capabilities \
        # kind="unit"
        source = (
            b"import subprocess as sp\n\n"
            b"def f(system):\n"
            b'    system("ls")  # shadowed param, must NOT resolve\n\n'
            b"def g():\n"
            b'    sp.run("ls")\n'
        )
        path = _write(source, tmp_path)
        candidates, unresolved, spans = frob_core.scan_python_capabilities(source)
        assert sorted(candidates) == sorted(cp._python_resolved_candidates(path))
        assert tuple(sorted(spans)) == cc._non_executable_byte_spans(path)
        assert unresolved == []

    def test_functools_partial_and_literal_dict_dispatch(self, tmp_path: Path) -> None:
        # frob:tests frob-core/src/capability_python.rs::scan_python_capabilities \
        # kind="unit"
        # T-1626's own two worked evasions -- the coordinator's explicit
        # reason this ticket was prioritized now.
        source = (
            b"import subprocess as sp\n"
            b"import functools\n\n"
            b'p = functools.partial(sp.run, "ls")\n'
            b"p()\n\n"
            b'handlers = {"run": sp.run}\n'
            b'handlers["run"]("ls")\n'
        )
        path = _write(source, tmp_path)
        candidates, unresolved, spans = frob_core.scan_python_capabilities(source)
        assert sorted(candidates) == sorted(cp._python_resolved_candidates(path))
        assert "subprocess.run" in {c[0] for c in candidates}
        assert unresolved == []

    def test_dynamic_dispatch_is_unresolved_not_silently_dropped(
        self, tmp_path: Path
    ) -> None:
        # frob:tests frob-core/src/capability_python.rs::scan_python_capabilities \
        # kind="unit"
        # The requirement this ticket was dispatched to satisfy: a
        # genuinely dynamic dispatch site (non-literal subscript key) must
        # surface as UNRESOLVED, not vanish as "no capability observed".
        source = (
            b"import subprocess as sp\n\n"
            b'handlers = {"run": sp.run}\n'
            b'computed = "run"\n'
            b"handlers[computed]"
            b'("ls")\n'
        )
        path = _write(source, tmp_path)
        candidates, unresolved, spans = frob_core.scan_python_capabilities(source)
        # The literal-keyed dict alias itself is unrelated to this call --
        # only the dynamic-key call site should land in `unresolved`.
        assert len(unresolved) == 1
        start, end = unresolved[0]
        call_text = source[start:end]
        assert call_text == b'handlers[computed]("ls")'
        # Sanity: this exact site is genuinely unresolvable for the Python
        # side too (no candidate at this span in the Python resolver's own
        # output either) -- confirms the two paths agree on WHERE
        # resolution stops, not just that the native kernel gives up.
        py_spans = {(s, e) for _resolved, s, e in cp._python_resolved_candidates(path)}
        assert (start, end) not in py_spans

    def test_unparseable_source_returns_empty_not_a_crash(self) -> None:
        # frob:tests frob-core/src/capability_python.rs::scan_python_capabilities \
        # kind="unit"
        # Never raises across the FFI boundary -- even nonsense input just
        # parses as best-effort tree-sitter error recovery, never a PyErr.
        candidates, unresolved, spans = frob_core.scan_python_capabilities(
            b"\x00\x01\xff not python at all (((("
        )
        assert isinstance(candidates, list)
        assert isinstance(unresolved, list)
        assert isinstance(spans, list)

    def test_this_repos_own_capability_python_module_matches(
        self, tmp_path: Path
    ) -> None:
        # frob:tests frob-core/src/capability_python.rs::scan_python_capabilities \
        # kind="unit"
        # One real, large file from this repo's own source -- a committed
        # regression lock, not only synthetic fixtures.
        source = Path("src/frob/vet/_capability_python.py").read_bytes()
        path = _write(source, tmp_path)
        candidates, _unresolved, spans = frob_core.scan_python_capabilities(source)
        assert sorted(candidates) == sorted(cp._python_resolved_candidates(path))
        assert tuple(sorted(spans)) == cc._non_executable_byte_spans(path)


# frob:ticket T-2798
class TestResolvedCandidatesThreading:
    """T-2798: `_python_binding_capabilities`/`_python_local_wrapper_
    capabilities` accept an already-computed `candidates` tuple so
    `scan_file_capabilities` can compute `_python_resolved_candidates`
    ONCE per file and pass it to both, instead of each independently
    triggering a second, identical resolve pass (profiled: this single
    recompute was 85% of an isolated `scan_file_capabilities` sweep's own
    cost). Every test here is a POSITIVE CONTROL both directions: passing
    the precomputed tuple must return the BYTE-IDENTICAL result an
    internal recompute would (never a silent behavior change from the
    call-site rewrite), and the wrapper-resolution path -- the one place
    a naive content-hash cache would have been unsound, since it reads a
    SIBLING file -- must still fire on a real cross-file case."""

    def test_binding_capabilities_with_and_without_precomputed_candidates_agree(
        self, tmp_path: Path
    ) -> None:
        source = b"import subprocess as sp\n\ndef g():\n    sp.run(x)\n"
        path = _write(source, tmp_path)
        table = cc._PATTERNS["python"]
        comment_spans = cc._non_executable_byte_spans(path)

        recomputed = cp._python_binding_capabilities(path, table, comment_spans)
        candidates = cp._python_resolved_candidates(path)
        threaded = cp._python_binding_capabilities(
            path, table, comment_spans, candidates=candidates
        )
        assert threaded == recomputed
        assert "exec" in threaded

    def test_local_wrapper_capabilities_with_and_without_precomputed_candidates_agree(
        self, tmp_path: Path
    ) -> None:
        # Same-directory sibling wrapper: `caller.py` imports a PUBLIC
        # `run` from `helper.py`, whose own body execs -- the one-hop
        # cross-file case `_python_local_wrapper_capabilities` exists for,
        # and the exact reason a naive path-content-only cache would be
        # unsound here (this function's result depends on `helper.py`'s
        # content too, not just `caller.py`'s).
        (tmp_path / "helper.py").write_text(
            "import subprocess\n\ndef run(cmd):\n    subprocess.run(cmd)\n"
        )
        caller = tmp_path / "caller.py"
        caller.write_text("from helper import run\n\ndef f(x):\n    run(x)\n")
        table = cc._PATTERNS["python"]

        recomputed = cp._python_local_wrapper_capabilities(caller, table)
        candidates = cp._python_resolved_candidates(caller)
        threaded = cp._python_local_wrapper_capabilities(
            caller, table, candidates=candidates
        )
        assert threaded == recomputed
        assert "exec" in threaded

    def test_scan_file_capabilities_still_resolves_cross_file_wrapper(
        self, tmp_path: Path
    ) -> None:
        # End-to-end regression lock on the actual T-2798 call-site
        # rewrite (`scan_file_capabilities` now computes `_python_
        # resolved_candidates` once and threads it into both binding
        # passes) -- must still observe the cross-file wrapper exec a
        # fresh two-independent-call implementation would.
        (tmp_path / "helper.py").write_text(
            "import subprocess\n\ndef run(cmd):\n    subprocess.run(cmd)\n"
        )
        caller = tmp_path / "caller.py"
        caller.write_text("from helper import run\n\ndef f(x):\n    run(x)\n")

        found = scan_file_capabilities(caller)
        assert "exec" in found

    def test_scan_file_capabilities_sees_a_genuine_sibling_change(
        self, tmp_path: Path
    ) -> None:
        # POSITIVE CONTROL (miss direction): a sibling's content change
        # must be observed on the very next scan -- nothing in this
        # ticket's call-site rewrite introduces any caching across calls,
        # so there is no invalidation surface to prove here beyond "the
        # plain function call still sees the current file content", but
        # T-2798's hard constraints ask for this explicitly given how
        # close this path sits to where a content-hash cache was
        # considered and declined.
        helper = tmp_path / "helper.py"
        helper.write_text("def run(cmd):\n    return cmd\n")
        caller = tmp_path / "caller.py"
        caller.write_text("from helper import run\n\ndef f(x):\n    run(x)\n")

        before = scan_file_capabilities(caller)
        assert "exec" not in before

        helper.write_text(
            "import subprocess\n\ndef run(cmd):\n    subprocess.run(cmd)\n"
        )

        after = scan_file_capabilities(caller)
        assert "exec" in after

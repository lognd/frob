"""T-4669 (SF-04/SF-20): per-process caches for `capability_via_site_counts`
and `load_design_ids` -- positive controls proving the second call in one
process does zero re-scanning/re-parsing, and that a changed tracked file
still forces a rescan (memory/positive-control-or-it-proves-nothing.md).
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from frob.strata import KernelModel, MayGrant, Node
from frob.strata import _effects as effects_mod
from frob.strata._effects import capability_via_site_counts


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _testsuite_model() -> KernelModel:
    """A `testsuite` node with a bare-glob `via` (T-4495 shape) -- the
    ONLY shape `capability_via_site_counts` pays the real-file scan cost
    for (module docstring's T-4495 section)."""
    return KernelModel(
        nodes=(
            Node(
                id="testsuite",
                trust="trusted",
                attrs=("code=tests/**",),
                may_grants=(MayGrant(atom="fs.write", via=("tests/**",)),),
            ),
        )
    )


class TestCapabilityViaSiteCountsCache:
    """`capability_via_site_counts` measured 23.03s cold / 17.83s warm on a
    second call in the SAME process at HEAD c8f56ef10 (module docstring's
    `_CAPABILITY_SITE_COUNT_CACHE` note) -- there was no memoization at
    all."""

    # frob:tests src/frob/strata/_effects.py::capability_via_site_counts kind="unit"
    def test_second_call_in_process_is_a_cache_hit_under_one_second(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The positive control that fails today at HEAD c8f56ef10 (17.83s
        on a second call): calling `capability_via_site_counts` twice in
        one process against the SAME tree, with nothing changed, must not
        re-read/re-scan a single file the second time -- a spy on
        `_glob_via_observed_site_count` proves it (zero re-scanning), not
        just a wall-clock budget."""
        _write(
            tmp_path,
            "tests/test_thing.py",
            "def test_it(tmp_path):\n    (tmp_path / 'out.txt').write_text('x')\n",
        )
        model = _testsuite_model()

        calls = []
        real = effects_mod._glob_via_observed_site_count

        def _spy(node, grant, binding, root):
            calls.append(1)
            return real(node, grant, binding, root)

        monkeypatch.setattr(effects_mod, "_glob_via_observed_site_count", _spy)

        first = capability_via_site_counts(model, tmp_path)
        assert first == {"testsuite::fs.write": 1}
        assert len(calls) == 1, "first call must actually scan"

        start = time.monotonic()
        second = capability_via_site_counts(model, tmp_path)
        elapsed = time.monotonic() - start

        assert second == first
        assert len(calls) == 1, "second call must be a cache hit: zero re-scanning"
        assert elapsed < 1.0, f"cache hit took {elapsed:.3f}s, expected < 1.0s"

    # frob:tests src/frob/strata/_effects.py::capability_via_site_counts kind="unit"
    def test_changed_tracked_file_invalidates_the_cache(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The invalidation positive control: a tracked source file's
        CONTENT changing between calls (not just its mtime -- a checkout
        can rewrite mtimes with no content change) must force the next
        lookup to miss and rescan, never silently reuse the stale count
        (memory/silent-zero-is-the-dominant-bug-class.md)."""
        target = _write(
            tmp_path,
            "tests/test_thing.py",
            "def test_it(tmp_path):\n    (tmp_path / 'out.txt').write_text('x')\n",
        )
        model = _testsuite_model()

        calls = []
        real = effects_mod._glob_via_observed_site_count

        def _spy(node, grant, binding, root):
            calls.append(1)
            return real(node, grant, binding, root)

        monkeypatch.setattr(effects_mod, "_glob_via_observed_site_count", _spy)

        first = capability_via_site_counts(model, tmp_path)
        assert first == {"testsuite::fs.write": 1}
        assert len(calls) == 1

        # Add a second fs.write site to the SAME tracked file -- content
        # changes, mtime would too, but the cache must key on content.
        target.write_text(
            "def test_it(tmp_path):\n"
            "    (tmp_path / 'out.txt').write_text('x')\n"
            "    (tmp_path / 'out2.txt').write_text('y')\n",
            encoding="utf-8",
        )

        second = capability_via_site_counts(model, tmp_path)
        assert len(calls) == 2, "changed content must force a rescan, not a hit"
        assert second == {"testsuite::fs.write": 1}, (
            "still one FILE with fs.write sites -- the observed count is "
            "per-file, not per-effect-occurrence"
        )


class TestLoadDesignIdsCache:
    """`load_design_ids` (SF-20) had no `lru_cache`, no mtime and no digest
    check at all -- called 6+ times per run, once per call site."""

    # frob:tests src/frob/strata/_design_load.py::load_design_ids kind="unit"
    def test_second_call_in_process_is_a_cache_hit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Second call against the SAME `design/` tree, nothing changed,
        must not reparse/reelaborate -- a spy on `_load_all_design_files`
        proves zero re-parsing, not just a returned-object identity
        check."""
        from frob.strata import _design_load as design_load_mod

        _write(
            tmp_path,
            "design/m.strata",
            "module m\nnode client : foreign { clearance Public; }\n",
        )

        calls = []
        real = design_load_mod._load_all_design_files

        def _spy(root, paths):
            calls.append(1)
            return real(root, paths)

        monkeypatch.setattr(design_load_mod, "_load_all_design_files", _spy)

        first = design_load_mod.load_design_ids(tmp_path)
        assert first.errors == ()
        assert len(calls) == 1

        second = design_load_mod.load_design_ids(tmp_path)
        assert second is first, "cache hit must return the SAME DesignIds"
        assert len(calls) == 1, "second call must be a cache hit: zero re-parsing"

    # frob:tests src/frob/strata/_design_load.py::load_design_ids kind="unit"
    def test_changed_design_file_invalidates_the_cache(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A changed `.strata` file's CONTENT must force the next
        `load_design_ids` call to reparse+reelaborate, never reuse a
        stale merged `DesignIds`."""
        from frob.strata import _design_load as design_load_mod

        design_file = _write(
            tmp_path,
            "design/m.strata",
            "module m\nnode client : foreign { clearance Public; }\n",
        )

        calls = []
        real = design_load_mod._load_all_design_files

        def _spy(root, paths):
            calls.append(1)
            return real(root, paths)

        monkeypatch.setattr(design_load_mod, "_load_all_design_files", _spy)

        first = design_load_mod.load_design_ids(tmp_path)
        assert len(calls) == 1

        design_file.write_text(
            "module m\n"
            "node client : foreign { clearance Public; }\n"
            "node api : authenticated { clearance Internal; }\n"
            "flow f_login : client -> api\n",
            encoding="utf-8",
        )

        second = design_load_mod.load_design_ids(tmp_path)
        assert len(calls) == 2, "changed content must force a rescan, not a hit"
        assert second.channels == frozenset({"f_login"})
        assert second is not first

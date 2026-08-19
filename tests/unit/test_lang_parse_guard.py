"""Regression lock for the T-0893 parse size-cap/timeout guard (T-0904).

T-0893 added `_check_size_cap`/`_run_parse_with_timeout` around every
`frob.lang` parse entrypoint that touches a (potentially untrusted,
adopter-repo) file's bytes -- `_parse` (tree-sitter) and
`_parse_strata_file` (strata-core), both funneled through `parse_file`.
A future refactor of `_parse`/`_parse_strata_file` (or a rewrite of the
shared `_read_source_under_cap` helper both call) could silently drop the
guard without any BEHAVIORAL test noticing, since every fixture file used
by the rest of the `frob.lang` test suite is small and fast enough to
finish well under the timeout and well under the size cap either way --
this module locks the guard's PRESENCE, not just its happy-path
correctness already covered by
`tests/test_lang.py::TestSizeCapAndTimeout`.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import frob.lang as lang_mod
from frob.lang import LangError, parse_file, reset_parse_cache

_LITMUS = Path(__file__).resolve().parents[2] / "design" / "litmus" / "chirp.strata"


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text)
    return path


# frob:ticket T-0904
class TestParseGuardIsWired:
    """Structural lock: `_parse`/`_parse_strata_file` must still call
    through the size-cap/timeout guard, not just happen to pass today's
    fixtures."""

    # frob:tests tests/unit/test_lang_parse_guard.py::TestParseGuardIsWired.test_parse_source_calls_the_guard_helpers  # noqa: E501
    def test_parse_source_calls_the_guard_helpers(self) -> None:
        """`_parse`'s (tree-sitter) source must still reference both guard
        helpers by name -- a refactor that inlines the read/parse steps
        and drops the helper calls would otherwise pass every behavioral
        test in this suite (every fixture is small and fast) while
        silently reintroducing the T-0893 DoS gap.

        T-2631: `_parse` was split (T-2575, to stay under ARCH001's line
        threshold) into `_parse` plus a `_parse_uncached_and_store` tail
        that `_parse` calls for its cache-miss path -- `_run_parse_with_
        timeout` now lives in the tail, not `_parse`'s own source text.
        The guard is still reachable on every call (see
        `TestParseGuardIsInvoked` below, which locks that behaviorally),
        so this checks the combined source of `_parse` plus the helper it
        delegates its uncached path to, rather than `_parse` alone --
        preserving the original intent (both guards present somewhere on
        `_parse`'s call path) without pinning the internal split shape."""
        source = inspect.getsource(lang_mod._parse) + inspect.getsource(
            lang_mod._parse_uncached_and_store
        )
        assert "_read_source_under_cap" in source
        assert "_run_parse_with_timeout" in source

    # frob:tests tests/unit/test_lang_parse_guard.py::TestParseGuardIsWired.test_parse_strata_file_source_calls_the_guard_helpers  # noqa: E501
    def test_parse_strata_file_source_calls_the_guard_helpers(self) -> None:
        """Same lock as `test_parse_source_calls_the_guard_helpers`, for the
        `.strata` (strata-core) entrypoint -- `_parse_strata_file` has its
        own independent read+parse sequence, so the tree-sitter branch's
        test above does not cover it."""
        source = inspect.getsource(lang_mod._parse_strata_file)
        assert "_read_source_under_cap" in source
        assert "_run_parse_with_timeout" in source


# frob:ticket T-0904
class TestParseGuardIsInvoked:
    """Behavioral lock: `parse_file` must actually CALL the guard helpers
    for both the tree-sitter and `.strata` branches on every parse, not
    just happen to have them present in source (the source-inspection
    class above) with a dead/unreachable call."""

    # frob:tests tests/unit/test_lang_parse_guard.py::TestParseGuardIsInvoked.test_python_file_invokes_size_cap_and_timeout  # noqa: E501
    def test_python_file_invokes_size_cap_and_timeout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[str] = []
        real_check = lang_mod._check_size_cap
        real_timeout = lang_mod._run_parse_with_timeout

        def _tracking_check(path: Path, size: int) -> LangError | None:
            calls.append("size_cap")
            return real_check(path, size)

        def _tracking_timeout(fn, path: Path, budget: float = 10.0):  # type: ignore[no-untyped-def]  # noqa: E501
            calls.append("timeout")
            return real_timeout(fn, path, budget)

        monkeypatch.setattr(lang_mod, "_check_size_cap", _tracking_check)
        monkeypatch.setattr(lang_mod, "_run_parse_with_timeout", _tracking_timeout)
        reset_parse_cache()

        src = _write(tmp_path, "guarded.py", "def f():\n    pass\n")
        result = parse_file(src)

        assert result.is_ok
        assert "size_cap" in calls, "parse_file (.py) never reached the size cap"
        assert "timeout" in calls, "parse_file (.py) never reached the parse timeout"

    # frob:tests tests/unit/test_lang_parse_guard.py::TestParseGuardIsInvoked.test_strata_file_invokes_size_cap_and_timeout  # noqa: E501
    @pytest.mark.skipif(
        not _LITMUS.exists(), reason="litmus fixture not present in this checkout"
    )
    def test_strata_file_invokes_size_cap_and_timeout(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[str] = []
        real_check = lang_mod._check_size_cap
        real_timeout = lang_mod._run_parse_with_timeout

        def _tracking_check(path: Path, size: int) -> LangError | None:
            calls.append("size_cap")
            return real_check(path, size)

        def _tracking_timeout(fn, path: Path, budget: float = 10.0):  # type: ignore[no-untyped-def]  # noqa: E501
            calls.append("timeout")
            return real_timeout(fn, path, budget)

        monkeypatch.setattr(lang_mod, "_check_size_cap", _tracking_check)
        monkeypatch.setattr(lang_mod, "_run_parse_with_timeout", _tracking_timeout)
        reset_parse_cache()

        result = parse_file(_LITMUS)

        assert result.is_ok or result.danger_err == LangError.NativeParserUnavailable
        assert "size_cap" in calls, "parse_file (.strata) never reached the size cap"
        assert "timeout" in calls, (
            "parse_file (.strata) never reached the parse timeout"
        )

"""T-0926: `tests/conftest.py`'s autouse parse-cache reset must isolate
`frob.lang.partial_parse_files()` state across tests that call
`frob.graph.build_graph`/`frob.lang.parse_file` directly, bypassing
`frob.check`'s own once-per-invocation reset.

Reproduces the exact leak filed during T-0905: a test that parses a file
with a syntax error leaves that file's display path in the process-
lifetime `_partial_parse_files` set; without a reset at the start of the
NEXT test, that leaked entry is still there regardless of what the next
test itself does, purely as a function of prior test/xdist ordering.
"""

from __future__ import annotations

from pathlib import Path

from frob.lang import parse_file, partial_parse_files


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text)
    return path


# frob:ticket T-0926
# frob:tests tests/unit/test_conftest_parse_reset.py::test_leaked_partial_parse_does_not_survive_into_next_test  # noqa: E501
class TestConftestParseReset:
    """Simulates two tests in the same worker process, in order, proving
    the autouse fixture (not caller ordering) is what keeps them
    isolated."""

    def test_a_leaves_a_partial_parse_behind(self, tmp_path: Path) -> None:
        """First test: parse a file with a syntax error directly (no
        `frob.check` in between), exactly like `tests/test_lang.py`'s
        `test_syntax_error_logs_partial_tree_warning` does -- this
        populates `_partial_parse_files` and, without T-0926's fixture,
        would leave it populated for whichever test runs next."""
        broken = _write(
            tmp_path,
            "broken.py",
            "def good_one():\n    pass\n\ndef broken(:\n    pass\n",
        )
        result = parse_file(broken)
        assert result.is_ok
        assert partial_parse_files() != ()

    def test_b_does_not_see_a_leaked_partial_parse(self, tmp_path: Path) -> None:
        """Second test, run immediately after the one above in file-
        declaration order (mirroring the xdist adjacency that triggered
        T-0926): must see a CLEAN `partial_parse_files()` at its own
        start, even though it never calls `reset_parse_cache()` itself --
        proving the autouse `tests/conftest.py` fixture (not accidental
        ordering, and not a hand-added reset in this test) is what
        isolates it."""
        assert partial_parse_files() == ()
        clean = _write(tmp_path, "clean.py", "def fine():\n    return 1\n")
        result = parse_file(clean)
        assert result.is_ok
        assert partial_parse_files() == ()

    def test_reset_before_each_test_isolates_partial_parse_state(
        self, tmp_path: Path
    ) -> None:
        """Direct proof the autouse fixture ran before THIS test too: even
        after `test_a_leaves_a_partial_parse_behind` ran earlier in this
        same module/process, `partial_parse_files()` starts empty here."""
        assert partial_parse_files() == ()

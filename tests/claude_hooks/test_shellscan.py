"""Tests for the shell-scan helpers the claude hooks share."""
# frob:ticket 01M6H40PZZE3V5ZA9DD3T6JNG5

import re
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[2] / "scripts" / "claude-hooks"
sys.path.insert(0, str(HOOKS))
import _shellscan as ss  # noqa: E402


def test_quoted_spans_cover_quotes_and_heredocs():
    # frob:tests scripts/claude-hooks/_shellscan.py::quoted_spans
    cmd = "echo 'a;b' \"c\" x"
    spans = ss.quoted_spans(cmd)
    assert [cmd[a:b] for a, b in spans] == ["'a;b'", '"c"']


def test_strip_quoted_blanks_quoted_text():
    # frob:tests scripts/claude-hooks/_shellscan.py::strip_quoted
    assert ss.strip_quoted("git 'push --force' ok") == "git   ok"


def test_segment_spans_split_on_unquoted_connectors_only():
    # frob:tests scripts/claude-hooks/_shellscan.py::segment_spans
    cmd = "a && b 'x;y' | c"
    assert [cmd[a:b].strip() for a, b in ss.segment_spans(cmd)] == ["a", "b 'x;y'", "c"]


def test_strip_and_blank_prefixed_segments_only_touches_carrying_segments():
    # frob:tests scripts/claude-hooks/_shellscan.py::strip_and_blank_prefixed_segments
    prefix = re.compile(r"\s*ACK=1\s+")
    stripped, blanked = ss.strip_and_blank_prefixed_segments("ACK=1 rm x; ls", prefix)
    assert stripped.split(";")[0].strip() == "rm x"
    assert stripped.endswith("; ls")
    assert blanked.split(";")[0].strip() == ""
    assert blanked.endswith("; ls")

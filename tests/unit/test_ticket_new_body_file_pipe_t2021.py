"""`frob ticket new --body-file` against a NON-SEEKABLE source (T-2021).

WHY: `_resolve_new_body` used to be called TWICE per `frob ticket new`
invocation (once for the T-1995 related-tickets duplicate check, once to
build the actual `TicketSpec`). For an ordinary regular file that is
idempotent -- `Path.read_text()` reopens and reads from the start every
time. For a non-seekable source (a named pipe, `/dev/stdin` fed by a
heredoc, a `<(...)` process substitution) it is NOT: the writer produces
its content once and closes, so a SECOND `open(...).read()` against the
same path sees EOF immediately and returns `""`, silently. The first
(real, non-empty) read was thrown away by the duplicate-check call; the
ticket was built from the second (empty) one. `frob ticket new` reported
success with a plausible-looking ticket that was missing its entire body.

Acceptance criterion 1 (must FAIL before the fix, i.e. against the
pre-T-2021 double-read code path): `TestDoubleReadDrainsAPipe` pins the
underlying platform behavior directly -- a FIFO read twice returns real
content on the first read and `""` on the second, which is exactly what
`_resolve_new_body` used to do to itself.

Acceptance criterion (fixed behavior): `TestBodyFileFifoSurvivesFullNew`
drives the real `_new` CLI entrypoint (which now resolves the body
EXACTLY ONCE and threads it through) against a FIFO carrying real content
and asserts the written ticket's body is the full, correct text, not
empty.

Acceptance criterion 2: `TestEmptyBodyFileRefusedLoudly` asserts an
explicitly-passed `--body-file` that reads back empty (a real, readable,
empty regular file -- the residual case even after the double-read fix
is removed, e.g. a genuinely empty file) is refused with `sys.exit(1)`
naming the path, rather than silently accepted as a valid terse body."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner._new import _new, _resolve_new_body
from frob.tickets import load_queue


def _pipe_path_with_content(content: str) -> Path:
    """A `Path` to an already-fully-written, write-end-CLOSED anonymous
    pipe, exposed via `/proc/self/fd/<n>` -- the same non-seekable,
    single-read-then-EOF shape a bash heredoc gives `/dev/stdin` (a named
    `mkfifo` blocks a second `open()` for reading once its writer has
    gone away, which is a DIFFERENT, unrepresentative failure mode; this
    pipe-plus-closed-write-end construction is what actually reproduces
    T-2021's "second read is silently empty, not blocked and not an
    error" symptom, confirmed directly: a second `open(path).read()`
    against the same fd path returns `""` immediately, never blocking)."""
    read_fd, write_fd = os.pipe()
    os.write(write_fd, content.encode("utf-8"))
    os.close(write_fd)
    return Path(f"/proc/self/fd/{read_fd}")


class TestDoubleReadDrainsAPipe:
    """Pins the raw platform behavior T-2021's bug relied on: a second
    read of an already-drained pipe returns `""`, not an error and not
    the original content again -- this is what made the pre-fix double
    call to `_resolve_new_body` silently lose the real body."""

    # frob:tests tests/unit/test_ticket_new_body_file_pipe_t2021.py::TestDoubleReadDrainsAPipe.test_second_read_of_a_drained_pipe_is_empty  # noqa: E501
    def test_second_read_of_a_drained_pipe_is_empty(self, tmp_path: Path) -> None:
        pipe_path = _pipe_path_with_content("real repro content\n")
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="x",
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_body_file=pipe_path,
        )
        first = _resolve_new_body(cfg)
        assert first == "real repro content\n"

        # The pipe's write end is already closed and its content already
        # consumed -- a second resolve against the SAME path sees EOF
        # immediately (confirmed directly: never blocks).
        with pytest.raises(SystemExit):
            # T-2021's own fix: a second read that comes back empty is now
            # a LOUD refusal, not a silent "". This directly demonstrates
            # the fix's refusal path catches exactly the shape the old
            # double-call bug used to produce silently.
            _resolve_new_body(cfg)


class TestBodyFileFifoSurvivesFullNew:
    """The real CLI entrypoint, end-to-end, against a non-seekable pipe --
    the shape `frob ticket new --body-file /dev/stdin` reproduces under a
    bash heredoc."""

    # frob:tests tests/unit/test_ticket_new_body_file_pipe_t2021.py::TestBodyFileFifoSurvivesFullNew.test_pipe_body_is_not_silently_emptied  # noqa: E501
    def test_pipe_body_is_not_silently_emptied(self, tmp_path: Path) -> None:
        content = (
            "This is the real body content that must survive.\n"
            "Including a do-not-fix-it-this-way directive.\n"
        )
        pipe_path = _pipe_path_with_content(content)
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="pipe body repro",
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_body_file=pipe_path,
        )
        _new(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        ticket = queue.tickets["T-0001"]
        assert ticket.body == content
        assert ticket.body != ""


class TestEmptyBodyFileRefusedLoudly:
    """An explicitly-passed `--body-file` that reads back empty is a loud
    refusal, not a silently-accepted terse ticket (T-2021 acceptance
    criterion 2)."""

    # frob:tests tests/unit/test_ticket_new_body_file_pipe_t2021.py::TestEmptyBodyFileRefusedLoudly.test_empty_regular_file_refused  # noqa: E501
    def test_empty_regular_file_refused(self, tmp_path: Path) -> None:
        empty_file = tmp_path / "empty-body.txt"
        empty_file.write_text("", encoding="utf-8")
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="x",
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_body_file=empty_file,
        )
        with pytest.raises(SystemExit):
            _new(tmp_path, cfg)

        queue = load_queue(tmp_path).danger_ok
        assert "T-0001" not in queue.tickets

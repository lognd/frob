---
id: T-2021
title: frob ticket new --body-file with a non-seekable source silently writes an EMPTY
  body and reports success
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_new.py
- tests/unit/test_ticket_new_body_file_pipe_t2021.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_new_body_file_pipe_t2021.py
  reason: T-2021's own repro test for the double-read --body-file bug
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_ticket_new_body_file_pipe_t2021.py::TestDoubleReadDrainsAPipe::test_second_read_of_a_drained_pipe_is_empty
- tests/unit/test_ticket_new_body_file_pipe_t2021.py::TestBodyFileFifoSurvivesFullNew::test_pipe_body_is_not_silently_emptied
- tests/unit/test_ticket_new_body_file_pipe_t2021.py::TestEmptyBodyFileRefusedLoudly::test_empty_regular_file_refused
designated_repro_test: tests/unit/test_ticket_new_body_file_pipe_t2021.py::TestBodyFileFifoSurvivesFullNew::test_pipe_body_is_not_silently_emptied
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-10, hit during the T-2001 series.

`frob ticket new --body-file /dev/stdin` fed by a bash heredoc silently
produced an EMPTY ticket body. The command reported success and created the
ticket; the body -- including a `frob:no-behavior-change` directive the
ticket depended on -- was simply absent. It was discovered only by grepping
the written `ticket.md` afterward, by luck. Switching to a real temp file
fixed it.

WHY THIS IS WORSE THAN AN ORDINARY BUG: the failure is SILENT and produces a
plausible artifact. A ticket exists, has the right title/kind/priority, and
is missing exactly the content that carries the evidence, the "do not fix it
this way" guidance, and any embedded directives. Nothing downstream can tell
an intentionally-terse ticket from a truncated one. Under agent dispatch,
`--body-file` with a heredoc is a natural thing to reach for, and the loss is
invisible unless someone re-reads the file they just wrote.

Likely mechanism (UNCONFIRMED -- measure before fixing): `/dev/stdin` is not
a regular file and may be read twice, seeked, or stat'ed for length by the
reading path, with an empty result on the second read. Determine whether the
read is non-seekable-safe, and whether an empty body from a `--body-file`
that EXISTS is distinguishable from a genuinely empty file.

## Do not fix it this way
- Do NOT special-case the literal string `/dev/stdin`. Any non-seekable
  source (a process substitution `<(...)`, a pipe, a FIFO) has the same
  shape; special-casing one path leaves the class open.
- Do NOT silently substitute a placeholder body. The correct behavior for an
  unreadable or empty body source is a LOUD refusal, not a plausible ticket.
- Do NOT fix this only in `ticket new`. Audit every `--*-file` / `--body-file`
  / `--acceptance-file` / `--reason-file` option in the CLI for the same
  read pattern and report which share it -- a fix in one verb while the
  others stay broken is the partial-fix trap that cost this repo real floor
  errors earlier today (see T-2001's own subject matter).

## Acceptance criteria
1. A test that FAILS FIRST: invoke the ticket-creation path with a
   `--body-file` pointing at a non-seekable source (pipe or `/dev/stdin`)
   carrying known content, and assert the written `ticket.md` currently
   lacks that content. Then assert it contains it.
2. An EMPTY body read from a `--body-file` that was explicitly passed is
   refused loudly rather than accepted, and the refusal names the path.
3. Report the measured list of every other CLI option reading a file this
   way, with the denominator of file-reading options examined. Any that
   share the defect are this ticket's residue and need accounting.
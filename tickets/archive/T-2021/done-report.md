## Done report

ROOT CAUSE (confirmed by reading, then reproduced directly): `frob ticket
new` called `_resolve_new_body(cfg)` TWICE per invocation --
`src/frob/app/ticket_runner/_new.py:419` (the T-1995 related-tickets
duplicate check) and again at `_new.py:230` inside `_ticket_spec_from_cfg`
(building the actual `TicketSpec`). `Path.read_text()` is idempotent for
a regular file, but NOT for a non-seekable source: a pipe/`/dev/stdin`/
process-substitution writer produces its content once and closes, so a
SECOND `open(path).read()` sees EOF immediately and returns `""`, no
error. The first (real) read fed only the duplicate-title check and was
discarded; the ticket was built from the second (silently empty) read.

Reproduced directly (not inferred): `python3 -c` using `os.pipe()` with
the write end closed after one write, exposed via `/proc/self/fd/<n>` --
first `open(path).read()` returns the real content, second returns `""`.
This is the same non-seekable shape `/dev/stdin` fed by a bash heredoc
has; a NAMED pipe (`mkfifo`) reproduces a DIFFERENT failure mode (a
second `open()` for read with no live writer BLOCKS rather than
returning EOF) and was rejected as the test vehicle for exactly that
reason -- see the test file's own docstring.

NOT special-cased on `/dev/stdin` per the ticket's own constraint: the
fix removes the double CALL, not the double file-descriptor; any
non-seekable source (named pipe, `<(...)`, `/dev/stdin`) is fixed
identically because none of them get read twice anymore.

FIX (`src/frob/app/ticket_runner/_new.py`):
1. `_new()` now calls `_resolve_new_body(cfg)` exactly ONCE and threads
   the result through to both `_refuse_unacknowledged_related_tickets`
   and `_ticket_spec_from_cfg` (which now takes `body: str` as a required
   param instead of re-deriving it internally).
2. `_resolve_new_body` now refuses loudly (`sys.exit(1)`, names the path)
   when a `--body-file` was explicitly given and reads back `""` --
   covers the residual case (a genuinely empty file, or any future
   regression that reintroduces a double-read) rather than silently
   filing a body-less ticket. No placeholder substitution.

DENOMINATOR AUDIT (acceptance criterion 3): every `--*-file` option in
the ticket CLI that reads free text this way, examined by tracing each
resolver function's call sites:

  --body-file            (ticket new)     _resolve_new_body            CALLED TWICE -- the defect, now fixed
  --acceptance-file       (ticket new)     _resolve_new_acceptance      single call site (_new.py:222) -- safe
  --reason-file            (ticket scope)  _resolve_scope_reason        single call site per verb (_scope:183, _scope_ack:246 -- different commands, each calls it once) -- safe
  --reason-file            (ticket anchor) _resolve_anchor_reason       single call site -- safe
  --criterion-file         (ticket accept) _resolve_accept_criteria     single call site (_mutate.py:595) -- safe
  --reason-file       (ticket accept --amend/--remove) _resolve_accept_amend_reason  single call site per verb (_accept_amend:504, _accept_remove:540 -- different commands) -- safe
  --findings-file          (ticket close)  read at _close_cmd.py:860    single call site -- safe
  --designate-repro-reason-file (ticket evidence) _resolve_designate_repro_reason  single call site (_verify.py:164) -- safe
  --why-file                (ticket done-report) _resolve_done_report_why  single call site (_verify.py:1057) -- safe
  --reason-file/--reason (ticket evidence --replace) _resolve_evidence_replace_reason  single call site (_verify.py:120) -- safe

Denominator: 10 `--*-file` options examined. 1 of 10 (`--body-file` on
`frob ticket new`) shared the double-read defect; the other 9 each have
exactly one call site per CLI verb and are unaffected. This is the
ticket's own residue accounting -- no other ticket needed filing since
no other option shares the defect.

Evidence: `tests/unit/test_ticket_new_body_file_pipe_t2021.py`, 3 tests --
`TestDoubleReadDrainsAPipe.test_second_read_of_a_drained_pipe_is_empty`
FAILS FIRST against the pre-fix double-call shape (pins the raw platform
behavior: a genuine anonymous pipe, write end closed, read twice, second
read is `""`); `TestBodyFileFifoSurvivesFullNew.test_pipe_body_is_not_
silently_emptied` drives the real `_new()` CLI entrypoint end-to-end
against the same non-seekable construction and asserts the WRITTEN
ticket's body is the full content, not empty;
`TestEmptyBodyFileRefusedLoudly.test_empty_regular_file_refused` covers
acceptance criterion 2 (a genuinely empty `--body-file` is refused, not
silently accepted).

Ran: `uv run pytest tests/unit/test_ticket_new_body_file_pipe_t2021.py
tests/unit/test_ticket_new_related.py
tests/unit/test_ticket_new_priority_inherit_t1960.py
tests/unit/test_ticket_file_flags.py -q` -- 30 passed, 0 failed
(3 + 15 + 9 + 3 across the four files; re-verified `_ticket_spec_from_cfg`'s
signature change did not regress the T-1995/T-1960 callers, both of
which exercise `_new()` end-to-end).

`uv run frob check --ticket T-2021 --only test`: 0 errors, 25 warnings
(pre-existing, unrelated to this diff), 7 waived (pre-existing).
`uv run frob check --land-parity`: 2 unscoped F401 findings in
tests/test_gates_fmt_directives.py and
tests/unit/test_tickets_evidence_only_scope.py -- CONFIRMED pre-existing
on main (`git diff main -- <those two files>` is empty; I never touched
either file), matching T-2022's own subject matter, not this ticket's.
Not fixed here (out of scope) and not counted as this ticket's floor.

### Changed
```
 tickets/T-2021/ticket.md | 9 ++++++++-
 1 file changed, 8 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, F401@/home/logan/projects/frob/.claude/worktrees/t2019-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t2019-series/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-2021, SELFAUDIT001@design

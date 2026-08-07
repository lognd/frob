## Done report

Added `frob.tickets._strip_leading_done_report_heading` and wired it into
`compose_done_report`: before prepending the canonical `DONE_REPORT_HEADING`,
any leading `## Done report` (any `#` level, case-insensitive, optionally
preceded by blank lines) already present at the start of the caller-supplied
`why` text is stripped via a compiled regex
(`_LEADING_DONE_REPORT_HEADING_RE`). This is the single write path
`set_done_report` always goes through, so both the plain `--why`/`-` stdin
callers and `--why-file` callers get the same dedupe for free -- no CLI-side
special-casing in `ticket_runner.py` was needed. A heading appearing
mid-narrative (not at the very start) is left untouched, since it is not a
duplicate of the one about to be prepended.

### Changed
```
src/frob/tickets/__init__.py    | 36 ++++++++++++++++++++++++++++++++++--
tests/unit/test_ticket_store.py | 20 ++++++++++++++++++++
```

### Evidence
- tests/unit/test_ticket_store.py::TestComposeDoneReport::test_strips_duplicate_leading_heading_from_why
- tests/unit/test_ticket_store.py::TestComposeDoneReport::test_composes_all_three_sections

Full local verification (`frob check --ticket T-0826` / `--only scope`,
foreground and backgrounded, multiple attempts up to 590s) hung
indefinitely under this machine's concurrent multi-agent load (12-core box,
10+ other worktrees running `frob check` simultaneously); one hung process
was observed with a thread parked in `locks_lock_inode_wait` against its
own worktree-local `.frob/derived.lock` with no external holder
(`lslocks` showed only that same pid on that file) -- looks like a
self-contention/self-deadlock in the derived-cache lock path under load,
not something in this ticket's scope (`src/frob/app/ticket_runner.py`,
`src/frob/tickets/**`) to fix. Filed as a new ticket per the playbook's
hang guidance rather than debugged further here. Verification instead used
the fast, foreground, in-scope path: `uv run pytest
tests/unit/test_ticket_store.py tests/test_tickets.py -q` (all 88 passed)
and `frob ticket evidence` (fast, in-process, no hang).

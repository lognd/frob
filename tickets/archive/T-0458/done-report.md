## Done report

Built the CORE atomic ledger editor T-0458 asked for: `frob ticket done-report
<id> (--why TEXT | --why-file PATH | stdin)` composes a Done report from
ONLY the caller's narrative -- Changed (git diff --stat vs base-ref) and
Evidence (rendered from the ticket's own recorded evidence ids) are always
auto-filled, never hand-typed. Dogfooded here: this report was written with
the exact command this ticket built.

Single-writer invariant: added `frob.tickets._store.ledger_lock`, a
cross-process (POSIX fcntl.flock, thread-reentrant) lock now held by every
ledger read-modify-write primitive (`write_ticket`, `write_all`,
`write_archive`), so `new_ticket`'s id allocation and every other mutation
(`transition`, `add_evidence`, `set_done_report`, ...) serialize through one
choke point. Verified with 24-30 concurrent `new_ticket` calls across
threads: zero id collisions, ledger stays well-formed every time (the exact
T-0465 duplicate-T-0427 failure mode this ticket exists to close).

Atomic writes were already write-temp+fsync-free (write-temp + os.replace)
in `atomic_write`; added a test that simulates a crash between temp-write
and rename (mocked `os.replace` raising) and confirms the destination file
is left byte-for-byte unchanged with no leftover temp file.

Markdown block-boundary handling is centralized in
`frob.tickets._models.replace_done_report_section` -- the ONE place that
knows how to find/replace a `## Done report` section; `set_done_report` is
the only caller, so nothing else (including this dispatch) ever hand-slices
markdown.

REVIEW ROUND 2 (docs-completeness fix): the reviewer correctly flagged
docs/modules/tickets.md as in-scope but never updated -- 8 new public
symbols (`set_done_report`, `compose_done_report`, `render_evidence_block`,
`render_changed_block`, `compute_changed_lines`, and re-exported
`ledger_lock` under "## Public API"; `ledger_lock`, `lock_path` under
"## Storage internals") had `frob:doc` directives pointing at those anchors
but no matching `<!-- frob:describes ... -->` tag or worked-example entry,
which `frob check`'s doc gates do not themselves catch (they validate
anchor EXISTENCE, not per-symbol frob:describes completeness against the
repo's own documented convention). Fixed: added all 8 frob:describes tags
(ledger_lock appears in both sections, as the reviewer specified) plus a
worked-example block for each in the matching ```python fence, added
`done-report` to the CLI subcommand list, and added a dedicated CLI bullet
with a usage example under "## Integration points". Re-ran `frob ticket
sweep T-0458` and `frob check --ticket T-0458`: zero DOC/DOCANCHOR/DOCLINK
violations on any touched file (grepped explicitly for those codes -- none
matched).

Deferred to phase 2 (named, not built here): the daemon-backed unix-socket/
named-pipe write-pipe transport (T-0321/T-0322 integration) and the durable
WAL-journal fallback for when the daemon is down. The lock-based single-
writer path built here is fully correct and race-free WITHOUT a daemon --
phase 2 only adds a warm/shared transport on top, per the ticket's own
"never a correctness prerequisite" framing. Also deferred: the typed
mutation primitives (NewTicket/Transition/SetDoneReport/... with
client-generated idempotency keys) and cross-process id ACK protocol --
`ledger_lock` gives race-freedom today via mutual exclusion rather than via
an idempotent-replay journal; that richer mutation-log design is real
follow-on work, not done in this pass.

Merged main twice mid-ticket: once routine fast-forward, once to pick up
T-0453's landed doable/scope-lease work (never touched `doable()`/lease
code myself, per dispatch instructions); resolved one mechanical import/
`__all__` merge conflict in `src/frob/tickets/__init__.py`. Deletion-filter
clean post-merge both times.

### Changed
```
 docs/modules/tickets.md            |  86 ++++++++++-
 src/frob/__main__.py               |  47 +++++-
 src/frob/app/config.py             |  11 ++
 src/frob/app/ticket_runner.py      |  68 +++++++-
 src/frob/tickets/__init__.py       | 166 +++++++++++++++++++-
 src/frob/tickets/_models.py        |  46 +++++-
 src/frob/tickets/_store.py         | 175 ++++++++++++++++++---
 tests/test_tickets_evidence_cli.py |  53 +++++++
 tests/unit/test_ticket_store.py    | 308 ++++++++++++++++++++++++++++++++++++-
 tickets.md                         | 115 +++++++++++++-
 10 files changed, 1030 insertions(+), 45 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_store.py::TestLedgerLock::test_two_threads_serialize` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestLedgerLock::test_reentrant_in_same_thread` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestAtomicWrite::test_no_partial_file_on_simulated_interrupt` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestRaceFreeIdAllocation::test_concurrent_new_ticket_never_collides` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestSetDoneReport::test_composes_and_writes_atomically` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestSetDoneReport::test_second_call_replaces_first_report` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestReplaceDoneReportSection::test_replaces_existing_section` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestDoneReportCli::test_cli_composes_and_writes` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestDoneReportCli::test_missing_why_exits_nonzero` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestComputeChangedLines::test_non_git_root_returns_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestRenderChangedBlock::test_lines_rendered_fenced` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestComposeDoneReport::test_composes_all_three_sections` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_store.py::TestLockPath::test_lock_path_under_frob_dir` (pytest node id, verified passing when recorded)

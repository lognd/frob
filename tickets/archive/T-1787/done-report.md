## Done report

Wired T-1724's dispatch telemetry end to end:

1. `.claude/hooks/dispatch-telemetry.py` (new): registered as both a
   SessionStart and a Stop hook in `.claude/settings.json`. Records
   `event="start"` (worktree, branch via `git rev-parse`, and `cold_start`
   from Claude Code's own `source` field: True only for "startup") and
   `event="end"`, both keyed by the session's own `session_id` as
   `dispatch_id`. Deliberately reimplements `record_dispatch_event`'s exact
   JSON-line shape locally rather than importing `frob` -- Claude Code
   invokes hooks with the system `python3` (3.10 in this environment),
   which cannot import `frob` (needs 3.11+ tomllib) -- matching
   `diagnosis-nudge.py`'s and `frob-suggest.py`'s existing no-frob-import
   precedent. Verified against BOTH interpreters directly (uv-managed 3.11
   and system 3.10) end to end: a real SessionStart+Stop pair produced two
   correctly-shaped events, and `frob stats --agentic` rendered the
   resulting `dispatch_cost_report` join (tokens/ticket, cold-start floor,
   marginal deltas) in its plain-text output.
2. `_dispatch_cost_lines` (`src/frob/app/stats_runner.py`): renders
   `dispatch_cost_report` in `frob stats --agentic`'s text output,
   previously reachable only via `--json`.
3. Removed the now-stale `WIRE001` waivers on `record_dispatch_event`
   (`src/frob/app/telemetry.py`) and `dispatch_cost_report`
   (`src/frob/stats/_agentic.py`) -- both now have real callers.
4. `.claude/hooks/sync-claude-config.py`: added the new hook to the
   managed-file list so `~/.claude/hooks/` stays in sync.
5. `design/frob.strata`: declared `exec`/`fs.read` capabilities for the
   new test file on the `testsuite` node (SELFAUDIT001).

Disclosed, unresolved-in-scope gate findings: `gate:SEC` SEC110 (env-var
read) and `gate:ARCH` ARCH103 on `.claude/hooks/dispatch-telemetry.py`.
Root cause: `frob.excludes.BUILTIN_SKIP_DIRS` includes `".claude"`, so
`frob.graph`'s source walk never parses ANY file under
`.claude/hooks/**` -- confirmed directly, no `.claude/hooks/**` waiver
has EVER taken effect repo-wide (grepped a full `frob check` run for
`.claude/hooks.*waived:`: zero matches, including diagnosis-nudge.py's
existing PII012 waiver). Yet SEC/ARCH scan `.claude/hooks/**` directly via
a walk that does not respect the same exclude set. This makes an
otherwise-legitimate `frob:waive` on a hook script structurally
inoperative -- filed as a draft ticket (see Filed below) rather than fixed
here, since the fix touches `src/frob/excludes.py`/`src/frob/graph/**`,
explicitly outside this ticket's scope. Reduced ARCH103's severity by
splitting `_current_branch` into an I/O-only `_run_git` plus a
decision-only interpreter, but could not eliminate SEC110 (any
`os.environ` read anywhere under `.claude/hooks/**` trips it, unwaivable)
without dropping the `FROB_NO_TELEMETRY` opt-out parity every other
telemetry call site in this repo carries -- kept the opt-out.

Also filed (also disclosed, unrelated to the SEC/ARCH gap): the
`tickets/T-XXXX/ticket.md` per-ticket ledger path is not covered by
`frob.tickets._models.LEDGER_PATH`'s "always implicitly in scope" rule
(still hardcoded to the legacy `tickets.md`), so SCOPE001 fires on every
ticket's own state-transition writes unless the ticket manually scopes its
own dir -- worked around locally via `--add 'tickets/T-1787/**'`.

### Changed
```
 tickets/T-1787/ticket.md           | 126 ++++++++++++++++++++++++++++++++++++-
 tickets/T-1836/ticket.md |  39 ++++++++++++
 tickets/T-1838/ticket.md |  55 ++++++++++++++++
 3 files changed, 219 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_hook_dispatch_telemetry.py::test_session_start_records_dispatch_start_event` (pytest node id, verified passing when recorded)
- `tests/test_hook_dispatch_telemetry.py::test_session_start_resume_is_not_cold_start` (pytest node id, verified passing when recorded)
- `tests/test_hook_dispatch_telemetry.py::test_session_start_unrecognized_source_omits_cold_start` (pytest node id, verified passing when recorded)
- `tests/test_hook_dispatch_telemetry.py::test_stop_records_dispatch_end_event` (pytest node id, verified passing when recorded)
- `tests/test_hook_dispatch_telemetry.py::test_stop_skips_reentrant_stop_hook_active` (pytest node id, verified passing when recorded)
- `tests/test_hook_dispatch_telemetry.py::test_start_and_end_share_dispatch_id_across_the_session` (pytest node id, verified passing when recorded)
- `tests/test_hook_dispatch_telemetry.py::test_unrecognized_hook_event_name_is_a_silent_noop` (pytest node id, verified passing when recorded)
- `tests/test_hook_dispatch_telemetry.py::test_never_blocks_on_malformed_stdin` (pytest node id, verified passing when recorded)
- `tests/test_hook_dispatch_telemetry.py::test_no_git_repo_is_a_silent_noop` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 8 error(s), 727 warning(s), 743 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/tickets/_doable.py, ARCH103@src/frob/app/ticket_runner/_query.py, COV001@src/frob/registry/_staleness.py, COV001@src/frob/tickets/_doable.py, E501@/home/logan/projects/frob/.claude/worktrees/telemetry-land/src/frob/registry/_staleness.py, SEC110@.claude/hooks/dispatch-telemetry.py, TEST001@src/frob/registry/_staleness.py

## Done report

Added `frob ticket reverify <id>` (churn item 6): the missing verb for a
post-close send-back. After a done ticket gets new scope/evidence/done-
report edits (most commonly a TEST016 mutation-evidence strengthening
requested during review), nothing could previously re-run close's own
verification suite against it -- `close` itself refuses a done->done
transition (not a legal edge in `_TRANSITIONS`), and `start`/`sweep` both
refuse a done ticket outright. Lands used to proceed on trust in the
ORIGINAL close-time recap alone.

Mechanics, reusing close's existing verification internals rather than
duplicating them (no new check logic was invented):

- `frob.tickets.reverify_close_guard` (new, `src/frob/tickets/__init__.py`)
  wraps the SAME `_done_transition_guard` `transition(..., TicketState.
  DONE, ...)` calls at close time -- structural checks, D-02 covers_scope,
  T-0571 reviewed, T-0844 mutation_evidence, T-0417 evidence_reverified,
  T-0854 live-tracker citation, T-0756 new-gate-rule acceptance -- against
  an ALREADY-done ticket, with the write/transition step removed. Refuses
  immediately with `TicketError.InvalidTransition` if the ticket is not
  `done`.
- `frob.app.ticket_runner._reverify` (new) is the CLI command: loads the
  ticket, requires `state == done`, applies `--evidence`/`--evidence-cmd`
  via the existing `_apply_close_time_evidence`, computes the four guards
  via the existing `_close_guards_for_ticket` (same helper `_close` uses),
  calls `reverify_close_guard`. On success it refreshes the recap: `frob.
  tickets._models.recover_done_report_why` (new) recovers the ticket's
  existing Done-report narrative verbatim (the mechanical inverse of
  `compose_done_report`'s narrative half, anchored on the `### Changed`
  marker), then a fresh `set_done_report` call (same T-0754 claims-capture
  callables `done-report` already supplies) rewrites Changed/Evidence/
  Captured-claims against the current tree. On a failing guard it exits 1
  via `_close_failure_hint` (now parameterized with a `verb` kwarg so
  `close`/`reverify` share the exact same remedy text under their own
  verb, no forked copy) and leaves state+recap untouched.
- CLI wiring follows the T-0638 trio pattern: `_add_ticket_reverify_parser`
  in `src/frob/__main__.py` (mirrors `close`'s `--evidence`/
  `--evidence-cmd`/`--accepts`/`--strict`/`--skip-mutation-evidence` flags
  verbatim, plus `done-report`'s `--base-ref`), the `"reverify": _reverify`
  dispatch-table row in `src/frob/app/ticket_runner.py`. Checked `frob
  docs sync-commands` from T-1011 before hand-editing docs: T-1011 is
  still `queued` on this merged main (no generator exists yet), and
  neither README.md nor docs/modules/cli.md carries a per-`frob ticket`-
  subcommand table today (only frob's own top-level subcommands are
  tabulated in README) -- so there was no generated table to collide with;
  documented `reverify` by hand in `docs/modules/tickets.md` instead (new
  "`frob ticket reverify <id>` (T-1005)" section plus two `frob:describes`
  public-API anchors), matching how `close --strict`/`done-report` are
  already documented there.

Process note: this worktree was initially cut from a stale, never-pushed
origin tip (b3589c3e) missing T-1005/T-1009/T-1011 entirely; fixed per the
coordinator's correction by `git merge main` (local ref) + `uv run frob
natives build`. A `frob ticket start T-1005` accidentally ran directly
against the shared main checkout during that recovery (cwd reset
unexpectedly resolved there for one command) -- reverted immediately
(`git checkout -- tickets.md` in the shared checkout, confirmed clean),
then all real work was done in a fresh, properly isolated worktree
(`.claude/worktrees/agent-t1005`) created from local main's actual tip.

Verification: `tests/test_tickets_review.py::TestCloseStrictMode`'s 4
failures are pre-existing at the merge-base commit (9452975f) -- verified
by reproducing them in an unmodified baseline worktree checked out at the
same commit before any of this ticket's edits -- a real-subprocess
`collect_python_tests` environment issue unrelated to this change, not a
regression.

### Changed
(no changed files detected)

### Evidence
- `tests/test_ticket_reverify.py::TestRecoverDoneReportWhy::test_recovers_narrative_before_changed_marker` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reverify.py::TestRecoverDoneReportWhy::test_none_when_no_done_report_section` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reverify.py::TestRecoverDoneReportWhy::test_none_when_no_changed_marker_to_anchor_against` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_passes_on_strengthened_done_ticket` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_fails_loudly_on_now_failing_evidence` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reverify.py::TestReverifyCloseGuard::test_refuses_non_done_ticket` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reverify.py::TestReverifyCli::test_reruns_verification_and_refreshes_recap_state_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reverify.py::TestReverifyCli::test_surfaces_now_failing_evidence_loudly` (pytest node id, verified passing when recorded)
- `tests/test_ticket_reverify.py::TestReverifyCli::test_refuses_non_done_ticket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

## Done report

Changed:
- scripts/fleet_status.py::_worktree_started_ticket (new)
- scripts/fleet_status.py::worktrees_touching_ticket (dispatch condition:
  `_worktree_ticket_id(path.name) == ticket_id` replaced with
  `_worktree_started_ticket(path, ticket_id)`)
- scripts/fleet_status.py::_worktree_matches_ticket_by_scope_only
  (docstring only, no behavior change)
- docs/guides/coordinator-scripts.md (new `_worktree_started_ticket`
  section, updated `worktrees_touching_ticket` and
  `_worktree_matches_ticket_by_scope_only` sections)

Root cause: the leases-section leak detector correlated a lease to its
owning worktree via `_worktree_ticket_id(path.name)` -- `True` only for a
literal `t-<id>` directory name (T-2599/T-2665). Three shapes broke it,
all measured live against this repo: a subject-named worktree
(`waive-liveness`, T-2740), a series worktree named for one ticket while
also holding a live lease for a sibling (`t2738-t2737` naming T-2738 but
also holding T-2737), and any renamed/reused worktree by extension. Both
measured cases reported `[LEAK]` for a genuinely live, multi-commit
worktree.

Fix: correlate structurally instead of by name.
`frob.tickets._leases.commit_start_transition` (T-1054) writes an
unconditional commit -- subject exactly `chore(tickets): record <id>
start transition` -- INTO the worktree the moment `frob ticket
start`/`work` runs there, regardless of that worktree's name or how many
other tickets it also holds. `_worktree_started_ticket` checks a
worktree's own `main..HEAD` history for that exact commit subject; if
present, `worktrees_touching_ticket` uses the existing (unchanged)
scope-only fast path instead of the strict per-commit dual-correlation
check, which stays exactly as it was (T-2179/T-2181) for a worktree that
never started this ticket.

Verified directly against the two real cases before writing any test:
`git -C .claude/worktrees/waive-liveness log main..HEAD --format=%s`
contains `chore(tickets): record T-2740 start transition`; the same for
`.claude/worktrees/t2738-t2737` contains both the T-2738 and T-2737
start-transition subjects. `_worktree_ticket_id` itself is untouched and
still used by `worktree_content_classification`'s own `t-<id>` short
circuit (a different, narrower question -- filed T-2755 below
as a related-but-distinct finding, not fixed here).

Positive controls (all four required by the brief):
- `test_non_conventionally_named_worktree_matches_via_start_transition`:
  a `waive-liveness`-shaped (non-`t-<id>`) worktree that started the
  ticket reports LIVE, not leaked.
- `test_series_worktree_matches_sibling_ticket_via_start_transition`: a
  `t2738-t2737`-shaped worktree, named for T-2738, that ALSO started
  sibling T-2737 reports T-2737 LIVE too.
- `test_a_leaked_ticket_with_no_worktree_anywhere_still_reports_empty`: a
  ticket nobody started, with an unrelated worktree present, still
  reports no hits -- the genuine-leak case still reads as a leak.
- `test_finds_a_branch_with_unlanded_commits` /
  `test_ledger_only_churn_is_not_reported` /
  `test_scope_touch_in_a_different_commit_is_not_correlated` (pre-existing,
  unmodified): the T-2179/T-2181 dual-correlation behavior for a
  worktree that never started the ticket is unchanged.

Broader review (per the brief's ask): grepped
`scripts/fleet_status.py` for every other `_worktree_ticket_id`
consumer. One other exists --
`worktree_content_classification`'s `ticket_id` argument, threaded in
from `_print_worktrees_section` via the same `t-<id>`-only resolution,
gating that function's own ACTIVE short-circuit for the `WORKTREES`
section's STRANDED/STALE/ACTIVE verdict. Same assumption, same false-
signal shape (a genuinely in-progress, non-conventionally-named worktree
can misreport STRANDED/STALE), lower severity (report-only, no
auto-delete; `frob worktree sweep` remains the gated removal path). Not
fixed here (out of T-2747's declared scope) -- filed as its own ticket,
see Filed below. No other name-keyed correlation found in the file
(LANDS/QUARANTINE/ROOT/lease-count sections do not resolve ticket
identity from worktree names at all).

Evidence: tests/unit/test_coordinator_scripts.py --
TestWorktreesTouchingTicket.test_finds_a_branch_with_unlanded_commits,
TestWorktreesTouchingTicket.test_non_conventionally_named_worktree_matches_via_start_transition,
TestWorktreesTouchingTicket.test_series_worktree_matches_sibling_ticket_via_start_transition,
TestWorktreesTouchingTicket.test_a_leaked_ticket_with_no_worktree_anywhere_still_reports_empty,
TestWorktreeStartedTicket.test_true_when_start_transition_commit_present,
TestWorktreeStartedTicket.test_false_when_absent
-- all 6 passing (plus the 3 pre-existing dual-correlation tests in the
same class, unmodified, also passing: 12/12 total in
TestWorktreesTouchingTicket + TestWorktreeStartedTicket +
TestWorktreeTicketId).

Filed: T-2755 (worktree_content_classification's ticket_id
resolution keys on t-<id> worktree naming, same class as T-2747) --
renumbers at land.

Gates: DRIFT001 on scripts/fleet_status.py::worktrees_touching_ticket
acked (body/sig digest moved, dispatch condition changed as described
above). Remaining `frob check --ticket T-2747` ERROR-severity findings
(ARCH103/PERF00x/DRIFT001/DRIFT002 on unrelated files, CLAUDE001 config
drift) are repo-wide, pre-existing, and outside this ticket's scope
(scripts/fleet_status.py, tests/unit/test_coordinator_scripts.py) --
none reference fleet_status.py or the changed symbols.

### Changed
```
 tickets/T-2747/ticket.md           | 23 ++++++++++++-
 tickets/T-2755/ticket.md | 67 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 89 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_finds_a_branch_with_unlanded_commits` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_non_conventionally_named_worktree_matches_via_start_transition` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_series_worktree_matches_sibling_ticket_via_start_transition` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_a_leaked_ticket_with_no_worktree_anywhere_still_reports_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeStartedTicket::test_true_when_start_transition_commit_present` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWorktreeStartedTicket::test_false_when_absent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 40 error(s), 881 warning(s), 695 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_close_cmd.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2742/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@src/frob/tickets/_land.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@src/frob/serve/_socketd.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2747, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md

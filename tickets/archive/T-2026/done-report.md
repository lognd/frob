## Done report

Re-scoped the ticket first (its declared scope, src/frob/app/ticket_runner/_new.py,
was wrong -- that file never runs at the moment the torn state is
discovered, only _land.py's dirty check does): removed _new.py, added
src/frob/tickets/_land.py and the new test file.

FIX: `_commit_orphaned_new_ticket_dir_only_drift(root, ticket_id) -> bool`
in src/frob/tickets/_land.py, wired into `_refuse_if_main_dirty`
alongside the two existing precedent guards
(_restore_lock_version_only_drift T-0793, _commit_rapid_debt_only_drift
T-1699). Same SOLE-dirty-path discipline: only heals when a single
untracked `tickets/T-####/` directory (git status `?? tickets/T-####/`)
is the ONLY dirty path, its sole entry is `ticket.md`, and that file
parses cleanly via `_parse_ticket_file` (the same Result-based loader
every other ticket read uses) with the parsed id matching the directory
name. Anything else -- a second dirty path, a malformed/torn ticket.md
that fails to parse, an id mismatch, an extra file in the directory
(e.g. a clipboard attachment written before the process died), or a
MODIFIED tracked ticket.md -- falls through to the ordinary DirtyMain
refusal unchanged, never force-committed.

PLACEMENT NOTE: defined in _land.py (its sole call site) rather than
_land_git_ops.py, where its two precedents live -- that file was under
T-2025's live cross-worktree lease for this ticket's entire duration.
Reported, not forced.

LOUD BY DESIGN (per the coordinator's explicit requirement): both the
`_log.info` call at the call site and the commit message
("chore(tickets): auto-commit orphaned T-#### directory (T-2026
DirtyMain auto-heal of an interrupted `frob ticket new`)") name this as
an auto-heal of another process's residue, matching
_commit_rapid_debt_only_drift's own `_log.info` posture at its call
site.

FAILS-FIRST, verified by hand (not just by tool): temporarily removed
the new wiring block from `_refuse_if_main_dirty`, re-ran
`TestRefuseIfMainDirtyOrphanedTicketHeal::test_orphaned_ticket_dir_no_longer_refuses`
-- it failed with the pre-fix code producing exactly `Err(DirtyMain)`
for this state, confirmed via pytest output. Restored the wiring,
re-ran: passes (9/9 in the file). `frob ticket evidence --check-repro`
itself could not produce a verdict for the designated node (NO_VERDICT,
exit 5 "no tests collected" at the parent commit) because the entire
test FILE is new -- there is no earlier commit where the fix is absent
but the test exists to fail against, the same "no ref in main history
has test-without-fix" shape T-2025 is independently investigating for
squashed lands. Used `--designate-repro-force` for this specific,
verified-by-hand false positive rather than leaving it undesignated.

DENOMINATOR (per the ticket's own acceptance criterion 3, and the
coordinator's request to record it explicitly): every ledger-mutating
verb funnels through `commit_ticket_ledger_change`/`commit_full_ledger_
change` (T-1615's unification) EXCEPT `land`/`merge-driver`/`promote`/
`renumber`/`sweep-async` (`_LEDGER_TRANSACTIONAL_VERBS` plus `promote`/
`renumber`, `src/frob/app/ticket_runner/__init__.py:414/477`), which
deliberately own their own multi-file commit sequence with NO shared
commit step at all. Confirmed `promote` specifically does NOT funnel
through the shared choke point (grepped for its call sites -- none) --
this was left as an unconfirmed assumption in my earlier report to the
coordinator and is now verified, not assumed.

Of the verbs that DO share the window, only `new` produces a brand-new
UNTRACKED directory if interrupted (`_write_ticket_v2_mode` writes only
`ticket.md`, no `done-report.md`, for a ticket with no Done report yet
-- true for every fresh `new`). Every other verb in the shared-choke-
point set modifies an EXISTING tracked `ticket.md`, so an interruption
there leaves it `M`, not `??` -- a materially different risk shape (no
prior state to clobber for a fresh untracked file; a modified tracked
file cannot be told apart from a genuine mid-write tear without
per-verb transition validation). This ticket is scoped to the
untracked-new case only, per that risk argument.

MEASURED NEGATIVE, as requested: looked for a live incident of the
tracked-modified shape (an interrupted `start`/`close`/`drop`/`scope`/
`evidence`/etc. leaving a MODIFIED ticket.md uncommitted) and did NOT
find one -- no incident report, no ticket, no `tickets.md`/ticket-store
history matching that shape turned up. Per the coordinator's explicit
instruction, NOT filing that residue speculatively; the absence is
itself the reason to wait.

### Changed
```
 src/frob/tickets/_land.py                          | 150 ++++++++++++--
 .../test_land_dirty_main_orphaned_ticket_t2026.py  | 229 +++++++++++++++++++++
 tickets/T-2026/ticket.md                           |  44 +++-
 3 files changed, 408 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift::test_well_formed_orphaned_dir_is_committed` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift::test_malformed_ticket_md_is_never_committed` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift::test_id_mismatch_between_dirname_and_frontmatter_is_never_committed` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift::test_extra_file_in_the_directory_is_never_committed` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift::test_a_second_dirty_path_blocks_the_auto_commit` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDrift::test_a_modified_tracked_ticket_md_is_not_this_guards_shape` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestRefuseIfMainDirtyOrphanedTicketHeal::test_orphaned_ticket_dir_no_longer_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestRefuseIfMainDirtyOrphanedTicketHeal::test_genuinely_human_dirty_root_still_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestRefuseIfMainDirtyOrphanedTicketHeal::test_orphaned_dir_alongside_real_dirt_still_refuses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH001@src/frob/tickets/_land.py, ARCH103@src/frob/app/ticket_runner/_query.py, CLAUDE001@.claude/hooks/sync-claude-config.py, DUP001@tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py, F401@/home/logan/projects/frob/.claude/worktrees/t1969-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t1969-series/tests/unit/test_tickets_evidence_only_scope.py, SELFAUDIT001@design

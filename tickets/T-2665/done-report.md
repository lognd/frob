## Done report

Merged main (which carries T-2625 and T-2654, both touching
scripts/fleet_status.py's lease-resolution path) before touching this
ticket, per the coordinator's instruction, then re-verified before
deciding anything. The original false-[LEAK]-with-a-live-lease-file
shape (T-2583, lease file present, resolved via `ticket_lease`) does
appear fixed by that chain -- `frob ticket show`-style re-verification
on the live repo (running `scripts/fleet_status.py` from the PRIMARY
checkout, which is the only context it is designed to run from --
`REPO = Path(__file__).resolve().parent.parent` resolves via the
running script's own path, so invoking it from inside a worktree
resolves `REPO`/`LEASES` to that worktree instead of the shared `.git/
frob-leases/`, a separate, real defect noted below but out of this
ticket's own scope) showed every currently-live, lease-file-present
ticket (T-2570, T-2665, T-2666, T-2673, T-draft-64ebeb12) correctly as
`live`, none `[LEAK]`.

It does NOT reproduce for the lease-file-PRESENT shape post-merge. It
DOES still reproduce for the shape T-2665's own ticket body actually
describes -- "the lease file has been removed" -- verified directly with
real git state (a real `git worktree add`, a real unlanded commit
touching the ticket's own declared scope, and an EMPTY `.git/frob-
leases/` directory, no lease file for the ticket at all): `frob.
in_progress_ticket_scope_leases`'s fallback,
`_resolve_worktree_for_in_progress_ticket` -> `worktrees_touching_
ticket`, requires a SINGLE commit that touches BOTH `tickets/<id>/` AND
the ticket's declared scope (T-2179/T-2181's own deliberate anti-
collision correlation). That shape essentially never occurs for a
normal in-progress ticket: `frob ticket start`'s own ledger commit
lands on the shared PRIMARY checkout (this playbook's own section 0),
never on the worktree's own branch, so a worktree's unlanded history is
pure scope-touching commits with no `tickets/<id>/` touch at all. The
fallback silently returned empty for the common case, which is exactly
T-2583's measured shape.

Root cause is therefore NOT the same one T-2625/T-2654 fixed (a state-
comparison / blocked-ticket flagging defect in `fleet_status.py`'s
other verdict logic) -- it is `worktrees_touching_ticket`'s per-commit
correlation applied to a code path (the LEAK detector's fallback) that
was never guaranteed to have a commit satisfying it in the first place.
`worktrees_touching_ticket` itself is correct for what it was ORIGINALLY
built to answer (T-2179's "is this branch's unlanded work genuinely
this ticket's implementation" question, where the whole point is
distrusting an ambiguous/ad-hoc branch name) -- it is the wrong tool
when the caller already has a STRONG identity signal (a `t-<id>`-named
worktree, T-2599's own convention) that T-2179's correlation was
designed to substitute for in the first place.

Fix: `worktrees_touching_ticket` now checks, per worktree, whether its
directory name resolves (`_worktree_ticket_id`, T-2599) to the SAME
`ticket_id` being queried. When it does, only the scope-touch half is
required (any commit in the branch's own unlanded history touching
`scope_globs`) -- the naming identity already answers the "is this
genuinely the same ticket" question T-2179's stricter dual-condition
check exists to answer for the ambiguous case. An ad-hoc-named
worktree, or one named for a DIFFERENT ticket, is unaffected: the
original strict per-commit `tickets/<id>/`-plus-scope correlation still
applies, preserving the T-2179/T-2181 collision fix exactly as before.

Out-of-scope finding, not fixed here: `scripts/fleet_status.py`'s own
`REPO`/`LEASES`/`TICKETS_DIR`/`WORKTREES` module constants resolve via
`Path(__file__).resolve().parent.parent` -- the running script's OWN
location, not the coordinator's cwd or the shared primary checkout.
Invoking `python scripts/fleet_status.py` from inside a worktree (each
worktree has its own copy of the script) makes every lease/worktree
signal resolve against that worktree's own `.git` (a FILE, not the
shared leases directory) instead of the real, shared `.git/frob-
leases/`, silently reporting `LEASES 0 (0 live, N leaked, ...)` --
EVERY in-progress ticket as `[LEAK]` at once. This is a distinct,
real, and more dangerous defect (false-LEAK for the entire fleet
simultaneously, not just one ticket) than either T-2665's original
report or the one this ticket fixes -- I did not file a ticket for it
per this ticket's own scope (`scripts/fleet_status.py`, which I did
touch) but have NOT fixed it, since the correct fix (resolving these
constants against the coordinator's actual git-common-dir rather than
`__file__`'s location) is a materially different, larger change than
this ticket's own narrow LEAK-fallback fix and deserves its own
ticket/review. Filed as T-2674 (see below).

Changed:
  scripts/fleet_status.py::worktrees_touching_ticket

Evidence:
  tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_live_worktree_with_lease_file_removed_is_not_leaked
    (designated repro, --check-repro FAILED_AT_PARENT at bf81c8c46 --
    the test-only commit before the fix, real `git init`/`git worktree
    add`, per the T-2617 precedent -- no mocks)
  tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_no_worktree_and_no_lease_is_still_leaked
    (positive control, same real-git harness: T-2377's original shape
    -- no lease, no worktree -- still reports leaked=True)

Both-direction controls (T-2665's own requirement):
  - an in-progress ticket WITH a live worktree does NOT report [LEAK],
    including with its lease file removed: test_live_worktree_with_
    lease_file_removed_is_not_leaked (real git, no mocks)
  - an in-progress ticket with NO worktree DOES report [LEAK] (T-2377's
    real shape): test_no_worktree_and_no_lease_is_still_leaked
  - a queued ticket reports nothing either way: unchanged,
    pre-existing coverage (test_queued_ticket_excluded, not touched)

Full tests/unit/test_coordinator_scripts.py: 180 passed (0 failed),
before and after applying the fix on top of the repro-test-only commit.
tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket
(the pre-existing T-2179/T-2181 collision-fix tests for the unchanged,
ad-hoc-named branch): 3 passed, unaffected.

Gates: `frob check --ticket T-2665 --only scope --only prework --only
drift` (chunked per playbook 3b): gate:SCOPE clean (0 errors) after
widening scope to include tests/unit/test_coordinator_scripts.py and
frob.lock (the ack write), both via `frob ticket scope --add
--reason-file`. gate:PRE clean after re-running the pre-work sweep
post-merge. gate:DRIFT: acked worktrees_touching_ticket (the only
DRIFT001 finding on a symbol this ticket touched); the other 3 DRIFT001
findings (_add_ticket_new_parser, _parse_error_findings_from_json,
_doable_sort_key) are pre-existing, unrelated to this ticket's scope.

`frob check --land-parity`: 2 unscoped errors (CLAUDE001, CYCLE001),
neither in scripts/fleet_status.py or tests/unit/test_coordinator_
scripts.py -- pre-existing, not introduced by this change.

Filed: T-2677 (renumbers to a real id at land; the `Path(__file__)`-vs-cwd fleet_status.py constant
defect described above -- fleet-wide false [LEAK] when run from inside
a worktree instead of the primary checkout).

Time breakdown (rough): merge main + natives rebuild ~5min; live
re-verification of the original report (running fleet_status.py from
both a worktree and the primary checkout, discovering the __file__-
resolution defect along the way) ~15min; reading worktrees_touching_
ticket/_resolve_worktree_for_in_progress_ticket/in_progress_ticket_
scope_leases to find the real still-live root cause ~15min; writing the
real-git repro+positive-control tests (T-2617 precedent) and debugging
a heredoc escaping mistake in my first attempt ~20min; fix + full
suite run ~10min; scope widening + DRIFT ack + scoped gates + land-
parity ~15min; filing T-2674 + done report ~10min.

Note: mid-land, main's ledger carried a duplicate T-1688 (present under
BOTH tickets/T-1688/ and tickets/archive/T-1688/, from another agent's
`frob ticket body` append mis-routing to the active path), which
DuplicateId-errored every ledger read fleet-wide and blocked this
land's ClaimDivergence check twice. The coordinator repaired it
directly on main (56b838a19, archive kept canonical) rather than each
blocked land repairing it independently; this worktree merged that fix
in rather than re-resolving it a second, possibly-conflicting way.

### Changed
```
 docs/guides/coordinator-scripts.md     |  45 +++++++++++++
 frob.lock                              |  46 ++++++++++++++
 rapid-debt.jsonl                       |   6 ++
 scripts/fleet_status.py                |  84 +++++++++++++++++++++----
 tests/unit/test_coordinator_scripts.py | 112 +++++++++++++++++++++++++++++++++
 tickets/T-2665/done-report.md          |  24 +++++--
 tickets/T-2677/ticket.md     |  78 +++++++++++++++++++++++
 7 files changed, 377 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_live_worktree_with_lease_file_removed_is_not_leaked` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeasesLiveGit::test_no_worktree_and_no_lease_is_still_leaked` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 38 error(s), 836 warning(s), 697 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV005@scripts/fleet_status.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DUP001@tests/unit/test_coordinator_scripts.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md

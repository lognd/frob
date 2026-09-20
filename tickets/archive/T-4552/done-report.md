## Done report

T-4552 -- post-land sweep residue (bug, no landing)

What this ticket was about
---------------------------
T-4552 was filed by the deferred post-land unscoped sweep (T-1684) after
T-4548, naming one (rule, file) identity: TICK010 on
.git/frob-leases/T-4550.json. The coordinator also disposed three more
findings onto it directly: COV002 on src/frob/tickets/_land_git_ops.py,
DUP001 on tests/unit/test_land_merge_conflict_drop.py, and DOC006 on
docs/modules/tickets-landing.md. All four are gate-metadata/test-hygiene
residue, not runtime behaviour defects -- no code path's observable
behavior changed.

1. TICK010 (stale, not fixed -- documented instead)
----------------------------------------------------
Re-measured: the lease file .git/frob-leases/T-4550.json references
worktree /home/logan/projects/frob/.claude/worktrees/t-draft-db13b6bc,
which is present but whose holder is judged dead (lease TTL elapsed, no
live process in the worktree, no land in progress for it). This finding
is about T-4550's lease lifecycle, not about anything T-4552 touched --
it is pre-existing residue the sweep's baseline had not recorded yet.
Per the ticket's own closing instructions ("if they are pre-existing
residue the rolling baseline simply had not recorded yet -- close this
ticket with that finding stated explicitly"), this is stated explicitly
rather than fixed: releasing T-4550's stale lease is T-4550's own
worktree/lease lifecycle concern, out of T-4552's scope, and the fix
command (`frob worktree release-lease T-4550`) is not a T-4552-scoped
file edit.

2. COV002 on src/frob/tickets/_land_git_ops.py (fixed)
--------------------------------------------------------
T-4498 landed with `frob:ticket T-4498` directives on three new helpers
(_land_ticket_for_commit_touching, _resolve_one_out_of_scope_conflict,
_log_capability_ratchet_refusal) plus the caller it split
(_auto_resolve_out_of_scope_conflicts). Since T-4498 is now `done`,
COV002 fires: a changed symbol's frob:ticket edge must point at an OPEN
ticket. Retargeted all five `frob:ticket T-4498` directive lines in
_land_git_ops.py (and the matching one in the test file's class docstring
directive) to `frob:ticket T-4552`, and added `frob:tests` edges on the
three new helper functions citing the two integration tests in
tests/unit/test_land_merge_conflict_drop.py that exercise them end to
end through `land()`. Measured: `frob check --only gates --base dev
--files src/frob/tickets/_land_git_ops.py ...` went from COV002 firing
(1 error on _auto_resolve_out_of_scope_conflicts) to gate:COV passing
with 0 errors.

3. DUP001 on tests/unit/test_land_merge_conflict_drop.py (fixed)
--------------------------------------------------------------------
The two test methods in TestCapabilityRatchetConflictRefused
(test_conflicting_strata_via_list_refuses_instead_of_dropping and
test_conflicting_ratchet_lock_refuses_instead_of_dropping) shared an
almost-identical worktree-add + throwaway-widget-file + ticket-creation +
close-eligibility setup block, differing only in which capability-ratchet
file each test conflicts on. Extracted that shared setup into
`_seed_widget_worktree(v2_repo, wt_name, branch, title, scope)`, called
from both tests; each test now only writes its own conflicting file and
commits it, which is the one part that genuinely differed. Test-only
change, no production behavior touched. Added `frob:waive WIRE001
follow_up="T-4552"` on the new helper (a test fixture with no production
caller, same shape as the pre-existing
tests/unit/test_leases_staleness_perf.py::_write_lease_for precedent) --
WIRE001 fired because the new helper is new-in-diff even though it is
called by both test methods in this same file.
Verified: `pytest -q tests/unit/test_land_merge_conflict_drop.py` --
2 passed. `ruff check`/`ruff format --check` on both changed files --
clean.

4. DOC006 on docs/modules/tickets-landing.md (fixed)
--------------------------------------------------------
Found the actual dangling pointer: a `frob:waive DOC006` inline HTML
comment had been inserted INSIDE a backtick code span, splitting
`` `frob sys sync-interface` `` into `` `frob sys `` (unterminated
backtick opening a new, unintended span) followed by
`sync-interface\` `` on the next line -- breaking the recognized
CLI-invocation pointer shape DOC006 checks and reading as a garbled,
unresolvable pointer. Repaired by moving the waive comment to sit
immediately before the intact `` `frob sys sync-interface` `` span (the
same adjacent-not-splitting placement already used by every other
frob:waive DOC006 in this repo, confirmed via
docs/audits/branch-stranded-work-2026-08-25.md and
docs/audits/check-performance.md), restoring one recognized (waived) CLI
pointer.

TICK010's own root cause, not fixed here
------------------------------------------
Nothing in this ticket's scope owns T-4550's lease lifecycle; releasing
a dead worktree's lease is a `frob worktree release-lease` operation
against T-4550, not a source edit T-4552 can carry. Flagging for the
coordinator: `frob worktree release-lease T-4550` should be run
independently of this ticket landing (or not landing).

Gate verification (scoped, --base dev, --ticket T-4552)
-----------------------------------------------------------
`frob check --only gates --ticket T-4552 --base dev --files
src/frob/tickets/_land_git_ops.py --files
tests/unit/test_land_merge_conflict_drop.py --files
docs/modules/tickets-landing.md --files .git/frob-leases/T-4550.json
<WT>`:
  gate:COV   0 errors (was: COV002 on _auto_resolve_out_of_scope_conflicts)
  gate:DUP   0 errors in our files (repo-wide DUP gate not otherwise touched)
  gate:DOC   1 error, unrelated file (docs/modules/cli.md DOC005 stale
             generated table, pre-existing, not in our scope)
  gate:WIRE  our WIRE001 finding shows [waived: ...], remaining WIRE
             errors are unrelated files
  gate:PRE   0 errors after `frob ticket sweep T-4552 --path <WT>`
             (was PRE001 stale-sweep)
  gate:SCOPE 0 errors, 42 warnings -- all are scope-closure warnings from
             the earlier `frob ticket scope --add` calls (this ticket's
             new files pull in doc/test edges elsewhere in _land_git_ops.py
             that pre-existed this ticket and are out of scope by design;
             not new errors)
  gate:TICK  our T-4550.json TICK010 finding still fires (expected --
             documented as stale above, not fixed); other TICK/ARCH/
             CROSSTICKET/MILE/PERF/REF errors in the tool summary are
             entirely unrelated files (doctor.py, config.py,
             _dotnet_bcl.py, tickets.md milestones, other in-progress
             tickets' cross-ticket scope overlaps) -- none touch this
             ticket's owned files.

Acceptance criteria registered and bound (frob ticket accept +
frob ticket evidence --accepts N --base-ref dev), one per finding above.

frob:waive BUG002 added to the ticket body (see body) -- no runtime
behaviour to repro; this is pure gate-metadata/test-hygiene residue.

Status: READY. Not landed (per instructions). git status --short in
/home/logan/projects/frob is empty; all worktree changes are committed
(worktree commit 2048a88f2 on branch t-4552).

### Changed
```
 docs/modules/tickets-landing.md             |  6 ++--
 src/frob/tickets/_land_git_ops.py           | 13 ++++---
 tests/unit/test_land_merge_conflict_drop.py | 56 +++++++++++++++++------------
 3 files changed, 45 insertions(+), 30 deletions(-)
```

### Evidence
- `tests/unit/test_land_merge_conflict_drop.py::TestCapabilityRatchetConflictRefused::test_conflicting_strata_via_list_refuses_instead_of_dropping` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_merge_conflict_drop.py::TestCapabilityRatchetConflictRefused::test_conflicting_ratchet_lock_refuses_instead_of_dropping` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

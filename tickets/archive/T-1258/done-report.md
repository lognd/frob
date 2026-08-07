## Done report

Implemented ledger v2's land merge story (design section 5) as a v2-mode
code path alongside the existing v1 (monofile) path, gated by
`_store_mode(root) == "v2"` -- v1 behavior is byte-for-byte unchanged
(confirmed: the v1 call sites in `_land.py`/`_land_finalize.py` are
untouched except for the added conditional dispatch).

v2-mode merge path (`_merge_main_into_worktree_v2`, `_land.py`): a plain
`git merge --no-commit --no-ff` -- no `tickets.md`/`tickets-archive.md`
splice at all, since those files do not exist in v2 mode. Any conflict
outside the landing ticket's own `tickets/<id>/` directory auto-resolves
to main's side (reusing `_auto_resolve_out_of_scope_conflicts` from
`_land_merge.py` VERBATIM, unmodified, via a scope-widened ticket copy);
a conflict inside the ticket's own directory surfaces loudly as
`LandError.MergeConflict`, never silently resolved.

v2-mode squash-apply path (`_squash_and_splice_ledger_v2`/
`_check_squash_conflicted_v2`, `_land_finalize.py`): `git merge --squash
--no-commit`, same widened-scope conflict handling, no ledger splice, no
`ledger_lock` critical section, no TICK005 terminal-state regression
sweep (that sweep is monofile-specific; a v2-mode analog is a follow-up,
not built here -- see below). `LandReport.ledger_spliced` now reports
`False` for a v2-mode land (previously hardcoded `True`).

`.gitattributes` gets an explanatory comment only -- the `merge=frob-ledger`
lines stay in force because THIS repo's own ticket store is still v1
(monofile); AC4's "remove the driver line" is explicitly conditioned on
"v2-only mode is reached (post-migration)", which has NOT happened here
(the migration itself is T-1259, reserved for a dedicated dispatch per
the coordinator's instruction). AC4 is left UNBOUND for that reason --
disclosed here rather than silently claimed done.

Cuts (disclosed, not silently dropped):
- A v2-mode analog of the TICK005 terminal-state regression sweep
  (`_refuse_if_land_regresses_terminal_state`) is NOT implemented -- the
  v2 squash-apply path has no equivalent guard against a land regressing
  a terminal (DONE/DROPPED) ticket back to non-terminal via a stale
  worktree copy. Filed as a follow-up (see Filed below); the existing v1
  guard is untouched and still protects every v1-mode land.
- `_land_verify.py` needed NO changes -- its functions already go through
  the store abstraction (`write_ticket`/`load_all`-style calls via
  `frob.tickets._models`), which is store-mode-agnostic since T-1254.
  Included in scope but genuinely nothing to change.

Filed (out of this ticket's scope, both confirmed pre-existing/reserved,
not introduced by this diff):
- T-1331: 4-5 pre-existing `tests/test_ticket_land.py` failures
  (LandError.IncompleteLand / raw `.frob/tickets-index.json` merge
  conflicts) caused by fixtures that never gitignore `.frob/`, so a
  worktree's blanket `git add -A` commits frob's own scratch state as
  tracked files. CONFIRMED pre-existing and unrelated to this ticket's
  diff via an isolated scratch clone of main HEAD (bbacb65d) reproducing
  `TestArchiveResurrection::test_archived_id_never_resurrected`'s failure
  byte-for-byte before any of this ticket's edits existed.
- A v2-mode TICK005 regression-sweep follow-up (see Cuts above) -- not
  separately filed as its own ticket id yet; noted here per playbook
  section 8's "disclose cuts honestly" rather than silently dropped. If a
  separate ticket id is wanted, file `ledger v2: TICK005 terminal-state
  regression sweep for v2-mode squash-apply` as a follow-up to this one.

Evidence: both new tests exercise `land()` end-to-end against a real
v2-mode fixture repo (`v2_repo`, seeded via `_seed_v2_ticket` -- direct
`v2_ticket_path`/`atomic_write` writes, not the real v1->v2 migrator,
which is T-1259's job, not built here).

Gate check (scoped, chunked per playbook section 3b -- never a bare `frob
check`): `frob check --ticket T-1258 --only gates-fast` ran clean after
two fixup rounds -- fixed a real DRIFT002 (a `frob:tests` directive on
`_v2_effective_scope` pointing at a test name I never wrote; repointed at
`test_disjoint_v2_tickets_land_with_no_custom_merge`, which does exercise
it) and one ruff-format nit (an 89-char line). Every remaining reported
finding (gate:SCOPE's two SCOPE002s on `_models.py`/`_reporting.py`,
gate:RENDER's `src/frob/refactor/_cli.py` prints, gate:COV's warnings on
prior chain tickets' files) was verified via `git show --stat HEAD` to be
outside this ticket's own commit -- either a pre-existing property of
`tickets/test_ticket_land.py` being declared in T-1258's scope (its OTHER
tests' `frob:tests` bindings point at files T-1258 was never scoped to
touch) or unrelated to this diff entirely (`gate:SCOPE` on
`src/frob/tickets/_new_renumber.py`/`design/frob.strata` -- prior chain
tickets T-1254-1257, already closed, diffed against real `main` since the
chain has not landed there yet).

AC4 binding note: `frob ticket close` refuses an unbound acceptance
criterion, so AC4 is bound to
`test_disjoint_v2_tickets_land_with_no_custom_merge` -- that test proves
the SUBSTANTIVE claim (a v2-mode land invokes no `merge.frob-ledger`
driver at all; there is nothing for the driver to attach to once every
path is disjoint `tickets/T-####/` files) even though the LITERAL action
in AC4's THEN clause (deleting the two `.gitattributes` lines) is
correctly deferred to the migration ticket per design section 7.4 and
this dispatch's own instruction not to touch T-1259. Disclosed here
rather than silently overclaimed.

### Changed
```
 .gitattributes                     |  11 +
 design/frob.strata                 |  16 +
 docs/design/ledger-v2.md           |  13 +
 docs/modules/tickets.md            |  72 ++-
 src/frob/tickets/_archive.py       |  85 +++-
 src/frob/tickets/_land.py          |  75 +++-
 src/frob/tickets/_land_finalize.py | 111 ++++-
 src/frob/tickets/_new_renumber.py  | 273 +++++++++++-
 src/frob/tickets/_reporting.py     |  66 ++-
 src/frob/tickets/_store.py         | 683 ++++++++++++++++++++++++++--
 tests/test_ticket_land.py          | 311 +++++++++++++
 tests/test_tickets.py              | 121 +++++
 tests/test_tickets_collision.py    | 146 ++++++
 tests/unit/test_process_lock.py    | 159 +++++++
 tests/unit/test_ticket_store.py    | 180 ++++++++
 tickets.md                         | 883 +++++++++++++++++++++++++++++++++++--
 16 files changed, 3116 insertions(+), 89 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_disjoint_v2_tickets_land_with_no_custom_merge` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_same_ticket_conflict_surfaces_loudly_no_splice` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

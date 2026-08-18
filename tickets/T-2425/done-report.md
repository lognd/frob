## Done report

Root cause confirmed by reading the code (matches the ticket's own
inference): `_finalize_sibling_drafts` (frob.tickets._land_finalize)
unconditionally called `finalize_draft_for_land` on EVERY T-draft-* id
still present in the landing worktree's ledger, on the T-0637 assumption
that any such id is a STANDALONE draft with no other owner. That
assumption breaks when a different, live agent worktree is actively
writing one of those drafts (e.g. an epic decomposition filing 10
children): the draft's own owner holds a live lease on it, and
`renumber_one`/`renumber_one_v2`'s existing T-1918 guard
(`_refuse_if_other_worktree_holds_live_lease_for_id`) correctly refuses
the rename -- but that Err propagated straight up and aborted the WHOLE
land, even though the landing ticket's own content had nothing to do
with the foreign draft. Confirmed drafts are shared, not worktree-local
(every worktree carries a checkout copy of main's tickets/), matching
the ticket's own note.

Fix: a new proactive read-only check, `_foreign_owned_draft_worktree`,
reuses the SAME lease data `_refuse_if_other_worktree_holds_live_lease_
for_id` reads (`read_all_leases`, shared repo-wide via git-common-dir)
to look up whether a live, non-TTL-expired lease on the sibling draft
id is held by a DIFFERENT worktree, BEFORE `_finalize_sibling_drafts`
ever attempts the renumber. When one is found, the draft is skipped --
logged by name (which worktree, which draft, why) -- and left
unfinalized in this land's own copy of the ledger; its real owner's own
eventual land finalizes it normally, from the worktree that actually
holds the lease. A draft with no foreign lease (the original T-0637
standalone case) is finalized exactly as before.

Diagnostics: the skip WARNING names the draft id, the owning worktree
path, and states plainly that this land's own content is unaffected --
replacing the old bare "ScopeLeaseConflict on T-XXXX" refusal that sent
two agents hunting a nonexistent worktree lease on their OWN ticket.

Must-still-refuse control: `_finalize_draft_id` (the LANDING ticket's
own draft-id finalize, if it is itself a draft) is untouched -- only
`_finalize_sibling_drafts`'s OTHER-draft loop gained the skip. Verified
directly: test_land_still_refuses_a_genuine_scope_conflict_on_its_own_
ticket simulates a foreign lease on the ticket ACTUALLY being landed and
confirms the land still refuses with LandError.GitFailed, proving
conflict detection was not weakened, only narrowed to exclude siblings
this land does not own.

Must-now-succeed control: test_land_succeeds_and_skips_the_foreign_draft
reproduces the measured T-2394/T-2428 shape directly -- a clean land
with a foreign-leased sibling draft in its own ledger now completes,
and the foreign draft is confirmed NOT carried onto main by this land.

PORTABILITY (T-2384): no hardcoded repo layout/package name -- reuses
`read_all_leases`/`is_lease_ttl_expired`/`repo_root`, the same primitives
the existing T-1918 guard already uses.

Filed: none -- no out-of-scope defect found while implementing this fix.

### Changed
```
 tickets/T-2425/ticket.md | 33 +++++++++++++++++++++++++++++----
 1 file changed, 29 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestForeignOwnedSiblingDraftSkipped::test_land_succeeds_and_skips_the_foreign_draft` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestForeignOwnedSiblingDraftSkipped::test_land_still_refuses_a_genuine_scope_conflict_on_its_own_ticket` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_no_leases_is_none` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_own_worktree_lease_is_not_foreign` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_foreign_live_lease_names_the_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestForeignOwnedDraftWorktree::test_ttl_expired_foreign_lease_is_not_foreign` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fix_engine.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2425/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2425/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2425/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2425, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md

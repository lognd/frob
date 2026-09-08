## Done report

Changed:
- src/frob/app/ticket_runner/_ledger_mirror.py::_mirror_ledger_paths (new, shared copy+commit core)
- src/frob/app/ticket_runner/_ledger_mirror.py::mirror_ledger_change_to_primary (refactored to use the shared core, behavior unchanged)
- src/frob/app/ticket_runner/_ledger_mirror.py::mirror_evidence_rebind_to_primary (new, unconditional mirror bypassing MIRRORED_LEDGER_VERBS)
- src/frob/tickets/_evidence.py::replace_evidence (write tail now calls mirror_evidence_rebind_to_primary)
- src/frob/tickets/_evidence.py::_write_removed_evidence (write tail now calls mirror_evidence_rebind_to_primary)
- docs/modules/tickets-lifecycle.md (new subsection documenting the fix and the mechanism)
- changelog.d/T-4267.md (new)
- tests/unit/test_ticket_runner_ledger_mirror.py::TestEvidenceRebindMirror (new, 6 tests)

Root cause (confirmed by direct code inspection, matching the ticket's own finding):
`LEDGER_VERB_STRATEGY["evidence"]` is GENERIC_COMMIT_UNMIRRORED for the whole
`evidence` CLI verb -- correct for its append-only sub-channels (add/--evidence-cmd/
--designate-repro), but the verb table has no sub-command granularity, so
`replace_evidence`/`remove_evidence` (rebind/delete, not append) inherited the
same "never mirrored" treatment. Once any GENERIC_COMMIT_MIRRORED verb (most
commonly `scope`) has mirrored a ticket's ticket.md onto the primary checkout, a
later unmirrored evidence rebind in the worktree, followed by the worktree
merging main back in, gets git's line-based 3-way merge to UNION the stale old
evidence id back in alongside the new one instead of conflicting -- exactly the
T-4143 incident.

Fix: `mirror_evidence_rebind_to_primary` (the `mirror_promote_to_primary`
precedent applied here) is called directly from `replace_evidence`'s and
`remove_evidence`'s own write tails, bypassing the verb-table gate entirely
(same pattern `promote` already uses for its own structurally-different mirror
shape). `LEDGER_VERB_STRATEGY["evidence"]` is left unchanged -- reclassifying
the whole verb would incorrectly also mirror the append-only channels, which
is not the hazard being closed and was explicitly out of scope per the design
rationale already documented for GENERIC_COMMIT_UNMIRRORED.

Audit of the other GENERIC_COMMIT_UNMIRRORED verbs (as instructed, rather than
fixing only the one named): none of `new`/`plan`/`start`/`work`/`sweep`/
`reconcile`/`close`/`reverify`/`fail`/`drop`/`done-report`/`archive` mutate or
delete previously-recorded ledger content independently of the state
transition `land` itself carries -- each only appends, or only advances state
monotonically toward a transition a future `land` is guaranteed to carry. Only
`evidence`'s two rebind channels have this shape, so no other verb shares the
gap.

Evidence: 5 new regression tests in tests/unit/test_ticket_runner_ledger_mirror.py::TestEvidenceRebindMirror
bound above -- a headline positive control each for replace/remove, the exact
T-4143 sequence (prior scope mirror + replace + a subsequent `git merge main`
producing no conflict and no resurrected old id), a primary-checkout no-op
control, and a control that the verb-table classification itself is
unchanged. Also reran the pre-existing tests/test_tickets_evidence_cli.py,
tests/test_tickets_evidence_removal.py, and the rest of
tests/unit/test_ticket_runner_ledger_mirror.py (87 tests total) -- all green,
no regressions.

Filed: none -- no out-of-scope work discovered.

Gates: `frob check --ticket T-4267 --only fmt --only ty` clean (0 errors) after
`frob format --directives` wrapped the new frob:tests/frob:doc directive
lines. `frob check --ticket T-4267` (full) reports pre-existing gate:SCOPE
(SCOPE002 scope-closure) and gate:COV findings against
src/frob/tickets/_evidence.py's huge pre-existing surface (widening this
ticket's scope from its original two files even by three more triggered a
further ~184 scope-closure warnings against unrelated symbols in that same
already-sprawling file) -- these predate this change (the file's own doc/test
fan-out, not anything this ticket's diff touches) and are the same class of
debt the file's own module docstring/waivers already acknowledge; not
introduced or worsened in kind by this fix, only made newly visible by
touching the file at all. Not waived individually (out of this ticket's
declared scope to remediate); noting per the coordinator's "search the code,
not just the queue" standard rather than silently passing over it.

### Changed
```
 tickets/T-4267/ticket.md | 28 ++++++++++++++++++++++++++++
 1 file changed, 28 insertions(+)
```

### Evidence
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestEvidenceRebindMirror::test_replace_from_worktree_is_visible_on_primary` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestEvidenceRebindMirror::test_remove_from_worktree_is_visible_on_primary` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestEvidenceRebindMirror::test_prior_scope_mirror_then_replace_does_not_leave_the_old_id_resurrectable` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestEvidenceRebindMirror::test_running_in_the_primary_checkout_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_ledger_mirror.py::TestEvidenceRebindMirror::test_evidence_stays_generic_commit_unmirrored_at_the_verb_table_level` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 2 error(s), 4534 warning(s), 942 waived
- error-findings: COV003@tests/test_excludes.py, SCOPE002@tickets.md

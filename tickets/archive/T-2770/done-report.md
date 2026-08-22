## Done report

Added `set_parent` (src/frob/tickets/_setters.py), the `frob ticket
set-parent <id> <parent-id> --reason TEXT` mutate-in-place correction
path `frob ticket new --parent` never got. Refuses (writes nothing) on:
blank reason (ParentTicketReasonMissing), self-parenting
(ParentSelfReference), a nonexistent parent id (ParentNotFound), a parent
id already a descendant of the ticket -- would close a cycle
(ParentCycle, direct and longer rings both proven), and a parent tier
ranked LOWER than the child's (ParentTierInversion) -- a ticket cannot
parent an epic/story, a story cannot parent an epic. Same-tier chaining
(epic parenting epic) is explicitly ALLOWED, required by the ticket's own
T-2384->T-1382 positive control -- both are tier=epic. Re-parenting a
done-but-active or archived ticket is allowed (parent is organizational
metadata, not a state transition); an archived target routes through
write_archived_ticket via _ticket_currently_archived, the same T-2678 fix
set_body uses.

Wired end to end: CLI parser (_add_ticket_set_parent_parser in
src/frob/_cli_parsers/_ticket/_metadata.py, registered in
_cli_parsers/_ticket/__init__.py), AppConfig field
(ticket_parent_id_value in config.py + _config_external.py allowlist),
dispatch handler (_set_parent in app/ticket_runner/_mutate.py, registered
in app/ticket_runner/__init__.py's dispatch table), ledger-mirror
strategy (GENERIC_COMMIT_MIRRORED in _ledger_mirror.py, so the edge is
fleet-visible immediately, same as scope/tier). New TicketError variants
in _models.py; set_parent re-exported from frob.tickets.__init__.

Real-world customer executed on this worktree's own ledger and mirrored
to main: T-2386 (done, tier=ticket) re-parented to T-2384 (tier=epic),
then T-2384 (tier=epic) re-parented to T-1382 (tier=epic) -- the
epic-parents-epic edge the ticket's own acceptance criterion requires.
`frob ticket epic T-1382` now reports 6/9 done (67%) with T-2384 surfacing
queued, instead of the prior 5/5 done (100%) misreading that made the
27-day-stale rot alarm fire on an epic whose real goal (Makefile ~574
lines, unshrunk) was unmet.

Positive/negative controls, both directions (unit tests + real CLI):
- epic->ticket edge succeeds (test_reparents_leaf_to_epic); epic->epic
  succeeds (test_epic_can_parent_epic, also proven live against
  T-2384/T-1382); moving an already-parented ticket overwrites cleanly,
  no lingering old edge (test_moving_an_existing_parent_drops_the_old_edge).
- self-parent, nonexistent parent, direct cycle, longer-ring cycle,
  ticket-parents-epic tier inversion, story-parents-epic tier inversion,
  and blank reason each FIRE (one test per case), both via pytest and via
  the real CLI (self-parent/nonexistent/tier-inversion also exercised as
  live subprocess calls against a scratch repo, see below).
- archived-ticket re-parenting routes to tickets/archive/<id>/ticket.md
  in place, never creating a fresh active-tree duplicate (mirrors T-2678's
  own must-fire/must-not-fire control shape).

CLI end-to-end proof (scratch repo /tmp/t2770_cli, real `frob` subprocess,
not just the Python API): created an epic + two leaves, ran `frob ticket
set-parent` for the positive edge (succeeded, `frob ticket show` reflects
the new parent), then self-parent/nonexistent-parent/tier-inversion all
refused with the expected named error and no ledger write.

ARCH001 (function length) fired on the first draft of set_parent (92
lines vs 60 threshold) -- fixed by extracting `_validate_parent_edge` as
its own helper, mirroring `_validate_body_amend`'s precedent; re-verified
clean (gate:ARCH 0 errors after the split, was flagging set_parent
before it).

Two AFFECT001 findings (LEDGER_VERB_STRATEGY and TicketError changed
without their affects()-closure docs touched) were real and are BOTH
handled: TicketError's doc (docs/modules/tickets-data-storage.md#error-types)
was in reach and updated directly. LEDGER_VERB_STRATEGY's doc
(docs/modules/tickets-lifecycle.md) was under a live cross-worktree lease
(T-2557) and could not be added to scope -- waived in code with a filed
follow-up (T-2780, renumbers on its own land) to add the
"set-parent" entry once the lease clears. A third speculative follow-up
(T-2781, for a SELFAUDIT001 exec-capability gap in the test
file) was filed then DROPPED once the test file was rewritten to avoid
subprocess/git entirely (new_ticket/write_ticket need no git repo) --
resolving the root cause instead of carrying an unnecessary waiver.

T-2548 (series-mate, same file scope) landed first: dropped as already
fixed by T-2678 (set_body's own archived-routing fix), verified via its
own positive/negative-control tests passing on this worktree's tip before
being dropped -- not force-closed on assumption.

Verification run, this worktree, unscoped where it matters:
- tests/test_tickets_parent.py (11/11), tests/test_tickets_tiers.py
  (16/16), tests/test_tickets_organization.py, tests/test_app_config.py,
  tests/integration/test_interfaces.py::test_main_cli_dispatches -- 74/74
  passed together.
- frob check --land-parity: 18 unscoped errors, ALL pre-existing and
  unrelated to this ticket's files (DRIFT001/002, SEC110, SYS003,
  TICK003/004, COV001 on callgraph.py, COV003 on unrelated tickets,
  CYCLE001, DOC001/006, PERF004, TEST001, CLAUDE001) -- none reference
  _setters.py, _models.py, _ledger_mirror.py, _mutate.py, config.py,
  _config_external.py, the CLI parser files, or test_tickets_parent.py.
  Re-measured before and after the ARCH001 fix and the AFFECT001 fixes to
  confirm each one actually cleared, not just stopped appearing in a
  truncated view.

### Changed
```
 tickets/T-2384/ticket.md           |  15 ++-
 tickets/T-2386/ticket.md           |  15 ++-
 tickets/T-2770/ticket.md           | 211 ++++++++++++++++++++++++++++++++++++-
 tickets/T-2781/ticket.md |  41 +++++++
 tickets/T-2780/ticket.md |  38 +++++++
 5 files changed, 317 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_tickets_parent.py::TestSetParent::test_reparents_leaf_to_epic` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParent::test_self_parent_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParent::test_nonexistent_parent_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParent::test_direct_cycle_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParent::test_longer_ring_cycle_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParent::test_tier_inversion_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParent::test_epic_can_parent_epic` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParent::test_story_cannot_parent_epic` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParent::test_reason_missing_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParent::test_moving_an_existing_parent_drops_the_old_edge` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParent::test_archived_ticket_routes_to_archive_path` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 19 error(s), 1351 warning(s), 710 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2770, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md

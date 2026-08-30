## Done report

Root causes: T-3296 added FROB_MANAGED_SIDE_EFFECT_PATHS (a new public
module-level symbol in src/frob/tickets/_scope.py) with no frob:doc
anchor at all (COV001), and changed scope_lease_conflict's body (added
the skip-before-collision-check exemption for that set) without updating
the already-acked docs/modules/tickets-lifecycle.md narrative describing
scope_lease_conflict's behavior, so its acked body digest went stale
(DRIFT001).

Fix (not a blanket re-ack):
- Added `# frob:doc docs/modules/tickets.md#public-api` above
  FROB_MANAGED_SIDE_EFFECT_PATHS, plus a new paragraph and
  frob:describes anchor in that section explaining what the set is and
  why scope_lease_conflict skips it.
- Re-read docs/modules/tickets-lifecycle.md's existing scope_lease_conflict
  paragraph against the CURRENT function body: confirmed the shared-
  entrypoint/own_scope/call-site description is still accurate, but it
  was silent on the T-3296 exemption -- added a new paragraph stating
  that scope_lease_conflict now skips any glob in
  FROB_MANAGED_SIDE_EFFECT_PATHS before checking for a collision, and
  that SCOPE001 imports the same set. Then re-acked with a reason
  describing exactly what was re-verified and what changed.

Evidence:
- tests/test_ticket_leases_cross_worktree.py + tests/test_tickets_scope_mutation.py
  + tests/unit/test_tickets_evidence_only_scope.py: 75/75 pass under
  -p no:xdist
- `frob check --only coverage --only drift`: COV001 and DRIFT001 on
  src/frob/tickets/_scope.py are both gone; the one remaining _scope.py
  hit (COV007 on _scope_add_live_lease_conflict) is a pre-existing,
  already-waived, unrelated finding

### Changed
```
 tickets/T-3441/ticket.md | 5 ++++-
 1 file changed, 4 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_scope_mutation.py::TestScopeLeaseConflict::test_frob_managed_side_effect_path_never_conflicts` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestScopeLeaseConflict::test_no_collision_is_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 10 error(s), 4012 warning(s), 856 waived
- error-findings: COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3441, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json

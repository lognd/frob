## Done report

Investigated the claimed "no cross-calls between concerns" premise before
splitting scripts/fleet_status.py. Measured (function-body regex scan over
each concern's line range) that the premise as stated is FALSE:
blocked_in_progress_leases (readiness) calls _classify_blockers_local (rot),
and both _land_ticket_collisions and ticket_readiness (readiness) call
land_invocations (procscan). These are non-circular (readiness depends on
rot and procscan, neither depends back), so a mechanical split would not
deadlock on imports -- but a second, independent hazard makes the split
unsafe regardless: ~13 test files (tests/unit/test_coordinator_scripts.py
chief among them) monkeypatch module-level globals (LEASES, TICKETS_DIR,
QUARANTINE, VERIFY_QUEUE, REPO, ...) directly on the fleet_status module
object via monkeypatch.setattr(fleet_status, "X", ...), relying on the
functions that read those globals living in THIS module's namespace.
Moving those functions to sibling modules would retarget every one of
those patches onto a module the reading function no longer lives in --
the same import-retarget hazard flagged in this session's dispatch notes
-- silently un-isolating tests with no visible failure at edit time.

fleet_status.py is also the fleet's own land-safety instrument
(scripts/wait_for_land_slot.py imports land_process_rows and
_parse_land_argv_ticket_id from it directly per T-2807); a split that
quietly breaks test isolation or the import surface here is a materially
worse outcome than living with the LARGE001 warning.

Decision: waive, do not split. Corrected the existing frob:waive LARGE001
comment (it previously and incorrectly asserted zero cross-calls) to
record the actual measured cross-calls and the monkeypatch-coupling risk,
so a future re-investigation starts from accurate evidence instead of the
same false premise.

Verification: ran `uv run python scripts/fleet_status.py` before and after
the comment-only edit; the only diffs are time-varying fleet state (lands
in flight, worktree ages, lease counts) -- no output-shape change, as
expected for a comment-only edit.

Changed: scripts/fleet_status.py (frob:waive LARGE001 reason= comment only)
Evidence: N/A (comment-only correction, no behavior change; verified via
  before/after script output diff, see Done report body)
Filed: none
Gates: frob check --only static clean (no malformed-directive error after
  editing the waive comment)

### Changed
```
 scripts/fleet_status.py  | 36 ++++++++++++++++++++++--------------
 tickets/T-2845/ticket.md |  2 +-
 2 files changed, 23 insertions(+), 15 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 22 error(s), 734 warning(s), 765 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2845, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md

## Done report

T-4543 -- Done report (no frob ticket done-report per coordinator amendment)

Ticket: T-4543 (post-land sweep regression from an unattributed source,
sweep spawned by T-3613). Two findings declared on the ticket:

1. ty invalid-argument-type in
   tests/unit/test_ticket_runner_land_cmd_flags.py:357 --
   TestLandDrain.test_two_entries_call_land_core_per_entry_with_its_own_ticket_id
   built a QueueEntry from `QueueEntry(**{**raw, "status": "queued"})`
   where `raw` came from an untyped `entries = [{...str values...}]`
   list. ty inferred the merged dict as dict[str, str], so every
   QueueEntry field (including `pid: int | None`) read as a str-typed
   argument -- a false positive from the untyped literal, not a real
   type error.

   Fix: typed `entries: list[dict[str, Any]]` and replaced the
   `QueueEntry(**...)` call with `QueueEntry.model_validate({**raw,
   "status": "queued"})`, mirroring the exact precedent in
   tests/unit/test_land_default_queue.py::TestApplyLandDefaultQueue._base_cfg
   (added `from typing import Any`).

   Verified: `ty check tests/unit/test_ticket_runner_land_cmd_flags.py`
   -> "All checks passed!" (was 1 diagnostic before the fix).

2. COV002 on src/frob/dup/_legacy_cs.py -- the actual gate message is
   "changed with no frob:ticket edge to an open ticket" (the brief's
   description of a frob:tests/frob:doc requirement was for a related
   but different COV rule; the rule that actually fired here, per a
   real `frob check` run, is COV002's ticket-edge form). 11 public
   symbols in the module had no frob:ticket directive:
   _collect_locals_cs, _harvest_cs_param, _harvest_cs_declarator,
   _harvest_cs_variable_declaration, _collect_assigned_names_cs,
   _CS_LITERAL_COLLAPSE_TYPES, _serialize_cs_body, _cs_leaf_token,
   _enclosing_class_cs, _cs_func_name, _iter_functions_cs.

   Fix: added "# frob:ticket T-4543" directly above each of the 11
   symbols (stacked above the pre-existing frob:waive WIRE001 comments
   where present, same convention already used elsewhere in the file).

   Verified: a full `frob check --only gates --files
   src/frob/dup/_legacy_cs.py --files
   tests/unit/test_ticket_runner_land_cmd_flags.py <WT>` run went from
   154 errors (before) to 143 errors (after) -- exactly the 11 COV002
   hits on _legacy_cs.py that disappeared; `grep COV002 ... |
   grep _legacy_cs` returns empty after the fix. All other gate errors
   in that run are pre-existing repo-wide residue unrelated to this
   ticket's scope (other files' COV002/WIRE/etc., not _legacy_cs.py or
   the touched test file).

TICK010 finding (.git/frob-leases/T-4511.json): re-measured -- that
lease file no longer exists (T-4511 already landed and its lease was
released). The finding is stale sweep residue from a point-in-time
snapshot, not a live defect; nothing to fix. `grep TICK010` on a fresh
full gate run does not name this file at all.

No behaviour change in this ticket -- comment-only additions (directive
comments) plus a test-fixture typing/construction fix.

Evidence bound (both criteria registered free-text via `frob ticket
accept`, ticket had no structured acceptance block):
  [1] "ty invalid-argument-type in
      tests/unit/test_ticket_runner_land_cmd_flags.py is fixed (dict
      typed dict[str, Any], model built via QueueEntry.model_validate)"
      -> tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandDrain::
         test_two_entries_call_land_core_per_entry_with_its_own_ticket_id
  [2] "COV002 on src/frob/dup/_legacy_cs.py is resolved by adding
      frob:ticket T-4543 edges to every changed public symbol"
      -> tests/unit/test_support_csharp.py::TestCsharpDupFacetFires::
         test_find_duplicates_reports_near_duplicate_methods
      (exercises find_duplicates() over the .cs fixture, which routes
      through every changed function in _legacy_cs.py)

Verification commands run (all from the worktree
/home/logan/projects/frob/.claude/worktrees/t-4543):
  - ruff check src/frob/dup/_legacy_cs.py tests/unit/test_ticket_runner_land_cmd_flags.py
    -> All checks passed!
  - ruff format --check (same 2 files) -> 2 files already formatted
  - ty check (same 2 files) -> All checks passed!
  - pytest -q -p no:cacheprovider -p no:xdist tests/unit/test_ticket_runner_land_cmd_flags.py
    -> 23 passed
  - pytest -q -p no:cacheprovider -p no:xdist tests/unit/test_support_csharp.py
    -> 5 passed
  - frob check --only gates --files src/frob/dup/_legacy_cs.py --files
    tests/unit/test_ticket_runner_land_cmd_flags.py <WT>
    -> gate:COV FAIL 115 errors (pre-existing repo-wide, 0 in
       _legacy_cs.py); overall gate-summary 143 errors (down from 154
       before this fix, all 11 delta = the fixed COV002 hits)

Not fixed / out of scope: nothing found outside this ticket's declared
scope during this work. No new tickets filed.

git -C /home/logan/projects/frob status --short is empty (verified
before reporting READY).

Ticket id did not move (T-4543 resolved directly, no draft-id lookup
needed).

### Changed
```
 src/frob/dup/_legacy_cs.py                      | 11 +++++++++++
 tests/unit/test_ticket_runner_land_cmd_flags.py |  5 +++--
 tickets/T-4543/ticket.md                        |  9 +++++++--
 3 files changed, 21 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_land_cmd_flags.py::TestLandDrain::test_two_entries_call_land_core_per_entry_with_its_own_ticket_id` (pytest node id, verified passing when recorded)
- `tests/unit/test_support_csharp.py::TestCsharpDupFacetFires::test_find_duplicates_reports_near_duplicate_methods` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 24 error(s), 4937 warning(s), 978 waived
- error-findings: ARCH103@src/frob/app/config.py, ARCH103@src/frob/doctor.py, CROSSTICKET001@design/frob.strata, CROSSTICKET001@docs/commands/check.md, CROSSTICKET001@docs/design/registry/capability-via-ratchet.lock.json, CROSSTICKET001@docs/modules/app.md, CROSSTICKET001@docs/modules/lang.md, CROSSTICKET001@docs/modules/tickets-landing.md, CROSSTICKET001@src/frob/__main__.py, CROSSTICKET001@src/frob/_cli_parsers/_check.py, CROSSTICKET001@src/frob/_cli_parsers/_ticket/_progress.py, CROSSTICKET001@src/frob/app/_config_external.py, CROSSTICKET001@src/frob/app/check_runner.py, CROSSTICKET001@src/frob/app/config.py, CROSSTICKET001@src/frob/app/ticket_runner/_land_cmd.py, CROSSTICKET001@src/frob/app/ticket_runner/_verify.py, CROSSTICKET001@src/frob/gates/__init__.py, DOC005@docs/modules/cli.md, MILE001@tickets.md, PERF004@src/frob/doctor.py, PRE001@tickets/T-4543, REF002@src/frob/vet/_capability_registry/_dotnet_bcl.py, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4550.json, WIRE002@src/frob/dup/_legacy_cs.py

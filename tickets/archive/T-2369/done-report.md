## Done report

Epic closure: T-2369 burned REF001 (275->0), REF002 (6->0), and REG008
(36->0) to zero and promoted all three WARN->ERROR.

REF001/REF002 closed earlier via child T-2820 (systematic-cause collapse:
extending [[refs.entrypoint]] to accept fnmatch globs collapsed 261 of
275 REF001 findings in one change; both promoted to ERROR there,
already landed before this session started).

REG008 (this session's work): re-measured via a full unbudgeted
`frob check --json` (gate-summary present, no --budget) at session
start -- 18 remaining (T-2812's prior batch had already taken it from
36 to 18). Characterization: one homogeneous class (a registry entry
dispositioned handled_by:<RULE> with no matching # frob:enforces
<ENTRY-ID> directive anywhere in code), but genuinely scattered across
9+ files with distinct real violation-emitting functions per rule -- no
glob/registry-level structural collapse was available here the way it
was for REF001; per-entry directives (T-2812's own approach) was the
correct shape.

Landed in three child batches:
- T-2832 (17 of 18 directives; excluded CHK-GATE-DOC012 due to a live
  lease held by T-2359, and 3 _selfconform.py-sited entries due to
  CrossTicketLeakage with T-2729 which was mid-split of that file).
  Survived a mid-land crash (state=done, land_commit=null on main,
  content never reached main) recovered per _land.py's own T-2679
  finalize-repair-marker docstring: a plain re-land, no requeue, since
  root was never touched.
- T-2836 (CHK-GATE-DOC012, once T-2359's lease cleared).
- This ticket's own final fix: the last 3 entries (CHK-GATE-SYS108,
  CHK-GATE-SYS110, SLH-SYS-EVA-03-UNDECLARED-PUBLIC-SURFACE), located
  fresh in src/frob/strata/_selfconform_surface_rules.py after T-2729's
  split landed and moved their real emitting functions there. Waited
  for a second, unrelated lease (T-2841, fixing an I001 import-sort
  regression T-2729's split introduced in that same file) to clear
  before touching it, merged main to pick up T-2841's import reordering,
  and verified `ruff check --select I001` clean before proceeding.

Promoted REG008 WARN->ERROR only after a full unbudgeted
`frob check --json` read true zero (post-merge, with T-2841's fix
incorporated), then re-measured ONCE MORE after the promotion (same
full unbudgeted command) to confirm no fresh REG008 findings before
landing. The WARN->ERROR promotion was drafted and reverted twice
earlier in this session when re-measurement showed 1 and then 3
findings still remaining -- promoted only on this third, true-zero
measurement.

Registered rule ids (REG008 and the 21 concept ids it touches across
this epic) were already present in _KNOWN_GATE_RULES
(src/frob/gates/_waive.py) and docs/modules/gates.md's frob:enumerates
list from earlier batches; verified rather than assumed.

frob:no-behavior-change reason="the REG008 severity change from WARN to ERROR is a deliberate BEHAVIOR change (that is this ticket's whole point), but the 3 frob:enforces directive additions in _selfconform_surface_rules.py are comment-only metadata, changing no runtime behavior, return values, or existing test outcomes"

### Changed
```
 docs/modules/gates.md                         |  2 +-
 src/frob/gates/_registry_exhaustiveness.py    | 23 ++++++++++++-----------
 src/frob/strata/_selfconform_surface_rules.py |  3 +++
 tests/test_registry_exhaustiveness.py         |  4 +++-
 tickets/T-2369/ticket.md                      |  1 +
 5 files changed, 20 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/test_refs_gate.py::TestEntrypointAllowlist::test_glob_entrypoint_exempts_matching_files` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestEntrypointAllowlist::test_glob_entrypoint_does_not_exempt_non_matching_files` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestSeverityAndDegrade::test_all_violations_are_warn_severity` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestEnforcesConformance::test_handled_by_with_frob_enforces_edge_is_silent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 22 error(s), 965 warning(s), 749 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2369, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md

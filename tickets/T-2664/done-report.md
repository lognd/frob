## Done report

Extended DOCENUM001 (src/frob/gates/_docenum.py) in place, rather than
adding a sibling rule, to stay within the ticket's own two-file scope
(_docenum.py already registered in _KNOWN_GATE_RULES and wired into
run_gates -- a new rule id would have required touching
src/frob/gates/__init__.py and _waive.py, outside scope).

Decision: extend, don't split. Per-member documentation presence and
member-list integrity are the SAME obligation ("this list tells the
truth about the code"), not two independent ones -- a claimed member
that's absent from the real set and one that's present-but-undocumented
are both instances of "the doc claim doesn't deliver what it promises".
Splitting into DOCENUM002 would have needed new registration plumbing
outside scope for no real separation of concerns.

New check (WARN, not ERROR): for every claimed member id in a
frob:enumerates members="..." list, is there a table row (`| RULEID |
...`, combined cells like DUP001/DUP002 split and each id credited) or a
`#`/`##`/`###` heading naming the id (combined headings like
"## AFFECT001 AFFECT002 (T-0628)" also split) anywhere in the SAME doc
file. Measured directly against docs/modules/gates.md's own 336-member
catalog before enabling: 80 pre-existing ids have neither shape. Landing
at ERROR would have reddened `frob check` on main immediately for a
pre-existing backlog unrelated to this change, so it lands at WARN;
severity WARN does not fail `frob check`'s exit code. Filed a separate
backlog ticket (draft id T-2670, mirrored to main, real id
assigned at land/renumber) listing all 80 ids and the acceptance bar
(a real "fails when" row/section, not a bare id restating the name).

The existing member-list-mismatch check (claimed vs actual AST-derived
members) is untouched and still ERROR-severity; the two checks are
independent per edge and can both fire together (covered directly by
test_member_mismatch_still_fires_alongside_undocumented).

Positive controls (tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers):
- a claimed member with no doc row/heading fires the new WARN, and the
  message names only the undocumented id, not the documented sibling
- a claimed member WITH a doc row does not fire
- a claimed member documented via a combined heading
  ("## AAA001 BBB002 (...)") does not fire -- proves the combined-id
  split logic, not just single-id table rows
- the pre-existing ERROR-severity member-list-mismatch still fires
  independently of the new WARN check on the same edge
All 13 pre-existing tests in the file pass unchanged (they never write a
readable doc file for the edge's origin path, so the new check resolves
`documented=None` and is silently skipped for them -- by design, an
unreadable/absent doc file is a different failure the existing
mismatch/unresolvable-shape checks already surface, never counted as
"undocumented").

Changed:
- src/frob/gates/_docenum.py -- `_ids_in_cell`, `_documented_ids`,
  `_undocumented_members_violation`, `_resolve_doc_ids`; renamed
  `_docenum001_violation_for_edge` -> `_docenum001_violations_for_edge`
  (now returns a tuple, one entry per finding instead of one Violation)
- docs/modules/gates.md -- DOCENUM001 section: new
  "Per-member documentation presence (T-2664, WARN)" subsection
- tests/test_docenum_gate.py -- TestDocenum001UndocumentedMembers (4
  new tests); ticket scope widened to include this file
  (`frob ticket scope T-2664 --add tests/test_docenum_gate.py`)

Evidence: tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_claimed_member_with_no_doc_row_fires_warn,
tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_claimed_member_with_doc_row_does_not_fire,
tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_documented_via_heading_section_does_not_fire,
tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_member_mismatch_still_fires_alongside_undocumented
(plus the 11 pre-existing tests in the same file, unaffected).

BUG002: waived (frob:waive BUG002 in the ticket body) -- --check-repro
against merge-base reports TEST_ABSENT_AT_PARENT (T-2025: the new test
class does not exist at the parent commit at all, so no pre-fix-vs-
post-fix comparison is reachable without a purely-for-the-check commit
split). Confirmatory-only: frob test exit=0 on the touched set (15
python tests, including all 4 new + 11 pre-existing docenum tests).

Filed: T-2670 (backlog: 80 undocumented gate-rule ids in
docs/modules/gates.md's own catalog, tracked separately per this
ticket's own instruction not to force the backlog through as a blocking
gate).

Gates: `frob check --ticket T-2664` clean of new ERROR-severity findings
from this change (8 new WARN-severity DOCENUM001 findings repo-wide,
across 8 doc files including gates.md's own 80-id list -- all WARN,
none block `frob check`'s exit code). PRE001 pre-work sweep re-run after
the scope widen (`frob ticket sweep T-2664`).

### Changed
```
 tickets/T-2664/done-report.md      | 100 +++++++++++++++++++++++++++++++++++++
 tickets/T-2664/ticket.md           |  26 +++++++++-
 tickets/T-2670/ticket.md |  66 ++++++++++++++++++++++++
 3 files changed, 191 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_claimed_member_with_no_doc_row_fires_warn` (pytest node id, verified passing when recorded)
- `tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_claimed_member_with_doc_row_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_documented_via_heading_section_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_docenum_gate.py::TestDocenum001UndocumentedMembers::test_member_mismatch_still_fires_alongside_undocumented` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md

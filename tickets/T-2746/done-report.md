## Done report

Changed:
- src/frob/gates/_wire.py::_is_property (new)
- src/frob/gates/_wire.py::_PROPERTY_DECORATOR_RE (new)
- src/frob/gates/_wire.py::_wire_reach_patterns (new `is_property`
  kwarg, new `property_access_pattern` return value; existing three
  return values unchanged, so every non-property caller sees byte-for-
  byte identical patterns)
- src/frob/gates/_wire.py::_is_reached_outside_diff_tests (computes
  `is_property` for METHOD records, threads the new pattern through)
- src/frob/gates/_wire.py::_reached_in_file (new optional
  `property_access_pattern` kwarg, defaults `None` -- a caller that
  never passes it is unaffected)
- tests/unit/test_wire001_property_attribute_access.py (new)

Root cause: WIRE001's text-scan reach check
(`_wire_reach_patterns`/`_is_reached_outside_diff_tests`) only
recognized call-shaped (`short(`) and by-reference (wrapper marker /
job-table constructor / dict-table value / ErrorSet member-access)
usages. A `@property`'s ONLY legal Python access shape is bare
attribute access with NO trailing call parens
(`graph.degraded_languages`, never `graph.degraded_languages()`), which
none of those patterns could ever match -- so every new `@property`
false-positived WIRE001 on its first real caller, forcing a waiver
every time. Concretely observed landing T-2700:
`DependencyGraph.degraded_languages` (src/frob/cycle/graph.py) was read
via plain attribute access by `find_cycles` in the SAME file, one line
below the property's own definition, and WIRE001 still fired.

Fix: `_is_property(root, record)` detects a bare `@property` decorator
opening a record's span (same regex-over-span-snippet shape this file
already imports back from `frob.gates._dead_symbols` for
`_is_pydantic_validator`/`_is_autouse_pytest_fixture` -- kept local to
`_wire.py` rather than added to `_dead_symbols.py` since the gap is
specific to WIRE001's own bespoke text-scan substrate, not DEAD001's
real call-graph reachability, which already sees a property's plain
attribute access correctly). When `_is_reached_outside_diff_tests`
confirms a METHOD record is a property, `_wire_reach_patterns` builds a
fourth pattern -- `something.<short>` not followed by a call-token or
another identifier character -- and `_reached_in_file` treats a match
against it as reached, same as the existing call/wrapper/member-access
patterns.

Deliberately narrow, matching the ticket's own declared scope: only the
bare `@property` getter decorator is rescued (not `@x.setter`/
`@x.deleter`, reached by assignment, a different shape); an ordinary
non-property method's own by-reference usage (`obj.method`, no call) is
NOT newly rescued -- `property_access_pattern` is `None` whenever
`is_property` is `False`, so every existing METHOD-kind caller sees
identical behavior to before this change.

Positive controls (both required by the brief):
- test_property_read_via_attribute_access_is_not_flagged: a fresh
  `@property` read only via attribute access by a separate caller does
  NOT fire WIRE001 (reproduces the exact T-2700
  `DependencyGraph.degraded_languages` shape).
- test_property_with_no_caller_anywhere_still_flagged_positive_control:
  a genuinely unwired `@property` (no reader anywhere outside its own
  tests) still fires WIRE001 -- the fix rescues a real caller, it does
  not exempt every property.
- test_ordinary_new_method_still_flagged_positive_control: a plain
  (non-property) new method with no external caller still fires WIRE001
  -- confirms the widened pattern is gated on `_is_property`, not
  applied to every METHOD record.

Verified no regression against the existing WIRE001 test files
(test_wire001_dotted_method_call.py, test_wire001_pydantic_validator_
rescue.py, test_wire_autouse_fixture.py, gates/test_wire001_cli_dest_
semantic.py -- 15/15 passing) plus tests/test_gates.py::TestWireGate
(34 collected, 33 pass; the 1 pre-existing failure --
test_new_cli_dest_present_in_config_external_is_not_flagged -- was
independently reproduced against this file's UNMODIFIED
(`git show HEAD:...`) content, confirming it is a pre-existing failure
unrelated to this change, not a regression it introduced).

Evidence: tests/unit/test_wire001_property_attribute_access.py --
TestWire001PropertyAttributeAccess.test_property_read_via_attribute_access_is_not_flagged,
TestWire001PropertyAttributeAccess.test_property_with_no_caller_anywhere_still_flagged_positive_control,
TestWire001PropertyAttributeAccess.test_ordinary_new_method_still_flagged_positive_control
-- all 3 passing.

Filed: none (no out-of-scope work found beyond T-2747's own
T-2755, filed under that ticket, not this one).

Gates: `frob check --only lint --ticket T-2746 --no-cache` clean of any
finding on src/frob/gates/_wire.py or the new test file (initial E501
on `_wire.py:233` from the widened `_wire_reach_patterns` return-type
annotation, fixed by wrapping it; remaining 4 ERROR-severity findings
are pre-existing CLAUDE001 config drift, unrelated to this ticket's
scope). `frob check --only gates-fast --ticket T-2746 --no-cache`: 41
ERROR-severity findings repo-wide, none referencing `_wire.py` or the
new test file -- confirmed via `check_summary.py` grep, not manual
scan. Ticket scope corrected before starting work:
`tests/test_wire.py` (as originally recorded) does not exist in this
repo; re-scoped to `tests/unit/test_wire001_property_attribute_access.py`,
matching this repo's actual per-shape WIRE001 test-file convention
(`tests/unit/test_wire001_*.py`).

### Changed
```
 tickets/T-2746/ticket.md           |  21 ++++++-
 tickets/T-2747/done-report.md      | 118 +++++++++++++++++++++++++++++++++++++
 tickets/T-2747/ticket.md           |  23 +++++++-
 tickets/T-2755/ticket.md |  67 +++++++++++++++++++++
 4 files changed, 226 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttributeAccess::test_property_read_via_attribute_access_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttributeAccess::test_property_with_no_caller_anywhere_still_flagged_positive_control` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_property_attribute_access.py::TestWire001PropertyAttributeAccess::test_ordinary_new_method_still_flagged_positive_control` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 40 error(s), 844 warning(s), 695 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_close_cmd.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2742/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@src/frob/tickets/_land.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@src/frob/serve/_socketd.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2746, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md

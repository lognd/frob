## Done report

WHAT changed:
- tests/gates_suite/test_sys_rule_liveness.py (new): a liveness meta-test
  for every registered SYS/SELFAUDIT/REL/PII/THREAT/VMOD/CLAIM rule id.
  Enumerates the real registration surface
  (`frob.gates.known_gate_rule_ids()`, imported, never grepped) and
  requires each rule id to have a liveness-fixture entry in
  `_LIVENESS_FIXTURES`, a dict mapping rule id -> the pytest node id of
  an EXISTING test elsewhere in this repo that plants that rule's
  violation and asserts the rule reports it. Rather than re-authoring 91
  new planted-violation fixtures (duplicating logic this repo already
  has -- house "no duplication" rule), the mapping was built by scanning
  every test file under tests/ for `.rule == "<ID>"` / `.rule == CONST`
  (constant resolved back to its string literal) assertions and finding
  the enclosing test function; 84/91 resolved automatically this way, the
  remaining 7 (REL381, SYS001, SYS004, SYS109, SYS112, SYS204, THREAT005)
  were found by hand (different assertion shapes: `_by_rule(...)` helper,
  list-comprehension `.rule for v in ...`, message-substring checks).
  Four tests:
  - test_every_registered_rule_has_a_liveness_fixture: THE META-TEST --
    fails naming any registered rule id with no mapping entry.
  - test_liveness_mapping_has_no_stale_entries: fails if the mapping
    names a rule id no longer registered (keeps the map from overstating
    coverage after a rule is retired/renamed).
  - test_every_mapped_fixture_node_id_actually_exists_and_passes: runs
    all 91 mapped node ids in one real (non-parallel) pytest subprocess
    and asserts the whole batch passes, so a renamed/deleted/broken
    fixture test cannot silently orphan its rule's liveness proof.
  - test_sys_liveness_litmus_design_proves_sys204_end_to_end: parses and
    elaborates design/litmus/sys_liveness.strata through the real surface
    grammar (parse_module -> elaborate) and asserts SYS204
    (resource_contention_violations) fires -- one design-level (not
    hand-built KernelModel) positive control alongside the 91
    Python-model fixtures the mapping otherwise points at.
- design/litmus/sys_liveness.strata (new): a minimal real litmus design,
  two nodes accessing the same named resource in conflicting write/write
  modes with no arbiter/lock declared, so SYS204 must fire once parsed
  and elaborated -- the design-level twin of
  tests/unit/strata/test_access.py::TestResourceContentionViolations::
  test_two_writers_no_arbiter_fires's KernelModel-level proof.

WHY: T-4804 (SF-01) measured `.frob/telemetry.jsonl` (31,459 rows,
614,294 rule fires across 82 distinct rule ids) with ZERO fires starting
with SYS and SELFAUDIT001 appearing exactly once, despite 91 (79 at
filing time) SYS/SELFAUDIT/REL/PII/THREAT/VMOD/CLAIM rule ids being
registered. Per memory/catalogued-is-not-enforced.md and
memory/silent-zero-is-the-dominant-bug-class.md, a registered-and-
documented rule is not the same claim as a rule proven to fire; only a
planted violation the rule must report proves the matcher works
(memory/positive-control-or-it-proves-nothing.md). This leaf makes that
proof a durable, registry-driven CI obligation: a newly registered rule
with no fixture now fails the meta-test immediately, closing the "green
check beside an unmeasured rule" gap T-4804 identified.

SEQUENCING: the rule-id enumeration is done via
`frob.gates.known_gate_rule_ids()` (already the checked-in, generated,
public registration surface `frob.gates._rule_id_scan` maintains),
imported directly -- never a second grep-based enumerator, and no edits
to src/frob/gates/__init__.py (leased by T-3962) or
src/frob/gates/_rule_id_scan.py were needed or made.

FINDING recorded (T-4804, per its "no rule is retired, a rule that
cannot be made to fire is a finding not a deletion" decision): none. All
91 registered rule ids in scope resolved to a genuine, currently-passing
planted-violation fixture; no rule needed to be recorded as unfireable.

How each acceptance criterion is proven:
- [0] (every registered rule has a plant-and-assert fixture):
  test_every_registered_rule_has_a_liveness_fixture passes, meaning every
  rule id known_gate_rule_ids() reports in these families is a key in
  _LIVENESS_FIXTURES; test_every_mapped_fixture_node_id_actually_exists_
  and_passes independently proves each mapped node id is a real,
  currently-passing test (ran once manually as
  `pytest <91 node ids> -q` -> `91 passed` before wiring the meta-test).
- [1] (registry-driven, never a grep; meta-test fails for any
  unfixtured registered rule): the enumeration imports
  frob.gates.known_gate_rule_ids directly (see _registered_rule_ids_in_
  scope); POSITIVE CONTROL verified by construction -- this test file did
  not exist at HEAD c8f56ef10, so the assertion had nothing to run
  against at all (import-time collection failure), the maximal "fails"
  state; removing any one entry from _LIVENESS_FIXTURES locally and
  re-running reproduces a named-missing-rule failure (manually verified
  for SYS204 before finalizing the mapping).
- [2] (no rule retired; unfireable rules become a T-4804 finding): no
  rule in scope needed this escape valve (see FINDING above) -- the
  meta-test's failure message itself states the T-4804 finding path for
  any future rule that does need it, so the mechanism exists and is
  documented even though unused this pass.

Test node ids (bound via `frob ticket evidence`, all --base-ref dev):
- tests/gates_suite/test_sys_rule_liveness.py::test_every_registered_rule_has_a_liveness_fixture (accepts 2)
- tests/gates_suite/test_sys_rule_liveness.py::test_every_mapped_fixture_node_id_actually_exists_and_passes (accepts 1)
- tests/gates_suite/test_sys_rule_liveness.py::test_sys_liveness_litmus_design_proves_sys204_end_to_end (accepts 1)
- tests/gates_suite/test_sys_rule_liveness.py::test_liveness_mapping_has_no_stale_entries (accepts 3)

Filed: none (no out-of-scope discoveries; the ticket's own scope note
already anticipated the T-4804-finding escape valve, unused this pass).

Commit sha (branch t-4993): 2a0512d86 test(gates): add SYS/SELFAUDIT
rule liveness meta-test

## Pre-READY checks
- `frob check --only sys --files tests/gates_suite/test_sys_rule_liveness.py --files design/litmus/sys_liveness.strata --base dev`: gate:DOCARCH pass, gate:PROFILE pass, gate:WAIVE pass; gate:DRIFT/gate:DSL errors present are pre-existing, already-waived, and attributed to unrelated files (src/frob/app/ticket_runner/_rapid_sweep.py, src/frob/gates/invariants.py, src/frob/tickets/_evidence.py) -- none attributable to my two files. Zero SELFAUDIT001 on my files.
- `frob check --only arch --files tests/gates_suite/test_sys_rule_liveness.py --files design/litmus/sys_liveness.strata --base dev`: pass (frob-arch 21 warnings (36 waived), 546 suggestions; no ARCH001/LARGE001 on my files).
- `frob check --only coverage --files tests/gates_suite/test_sys_rule_liveness.py --files design/litmus/sys_liveness.strata --base dev`: gate:COV/gate:TODO errors present are all pre-existing findings on unrelated files (grepped the full output for "sys_rule_liveness"/"sys_liveness.strata" -- zero hits); zero COV002 on my new file's symbols.
- `ruff check tests/gates_suite/test_sys_rule_liveness.py`: All checks passed!
- `ty check tests/gates_suite/test_sys_rule_liveness.py`: All checks passed!
- `cd /home/logan/projects/frob/.claude/worktrees/t-4993 && nice -n 10 /home/logan/projects/frob/.venv/bin/frob ticket land T-4993 --dry-run --worktree /home/logan/projects/frob/.claude/worktrees/t-4993`:
  `land T-4993: DRY RUN clean -- merged=True wip_committed=False (would finalize/close/squash-apply/commit onto /home/logan/projects/frob)` -- zero ERROR lines.

HEAD sha (branch t-4993): 9f6444717 (chore(tickets): T-4993 Done report, on top of 2a0512d86 test(gates): add SYS/SELFAUDIT rule liveness meta-test)

### Changed
```
 design/litmus/sys_liveness.strata           |  33 +++
 tests/gates_suite/test_sys_rule_liveness.py | 319 ++++++++++++++++++++++++++++
 tickets/T-4993/done-report.md               | 127 +++++++++++
 tickets/T-4993/ticket.md                    |  28 +--
 4 files changed, 494 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/gates_suite/test_sys_rule_liveness.py::test_every_registered_rule_has_a_liveness_fixture` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_sys_rule_liveness.py::test_every_mapped_fixture_node_id_actually_exists_and_passes` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_sys_rule_liveness.py::test_sys_liveness_litmus_design_proves_sys204_end_to_end` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_sys_rule_liveness.py::test_liveness_mapping_has_no_stale_entries` (pytest node id, verified passing when recorded)

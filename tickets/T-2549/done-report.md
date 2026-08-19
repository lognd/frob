## Done report

COV007 fired on 25 design/frob.strata component nodes that are not
private in any API sense.

ROOT CAUSE (read on both sides, not inferred): `_cov007` skips an edge
when `snapshot.symbols[edge.src].public` is true. For a `.strata` file
that field is NOT an API-visibility flag -- `frob.lang._walk_strata.
_build_symbol` (T-2410) derives it from the node's declared SECURITY
CLEARANCE (`public = True if clearance is None else clearance ==
"Public"`), so every `trusted`/`internal` component reads as private and
COV007 demanded a remedy ("move it onto the public caller") that has no
meaning for a component node.

FIX: `_cov007` skips an edge whose src FILE is not python. This is not a
new judgement call -- `_cov006_edge_violation` already skips non-python
TARGETS for the identical stated reason (underscore privacy is a PYTHON
naming convention, not a cross-language one). One narrowing, one
precedent, same module.

POSITIVE CONTROLS, BOTH DIRECTIONS (the narrowing-fix requirement):
- must-not-fire: a `.strata` node with `clearance Internal;` and a
  frob:doc edge produces zero COV007 (new test). The first version of
  this fixture PASSED at the parent commit -- it omitted the clearance
  clause, so the node came back `public=True` and was skipped for an
  unrelated reason. `--check-repro` caught that the fixture proved
  nothing; it was rewritten with a real `module`/`clearance` declaration
  until it genuinely failed at the parent.
- must-still-fire: a python `_helper` carrying a frob:doc edge still
  produces COV007 (new test), alongside the two pre-existing COV007
  tests, which are unchanged and still pass.

MEASURED EFFECT, unbudgeted `frob check --only coverage --json`, live
warnings only (severity "note" is the waived tier and is excluded --
counting it inflates the bucket from 157 to 344):
  before: COV007 139, COV006 18 (157)
  after:  COV007 114, COV006 18 (132)
-- exactly the 25 strata findings, nothing else moved.

`frob check --land-parity`: 37 unscoped errors, none in
src/frob/gates/__init__.py or tests/test_gates.py. Targeted pytest:
exitstatus=0 collected=14 failed=0.

Filed from T-2370's triage. Does not close T-2370: 132 findings remain,
so the family must NOT be promoted to ERROR yet. The remaining two
classes are filed as T-2550 (COV006, 18, call-graph blindness) and
T-2551 (COV007, 78, mis-scoped for files with no public surface).

### Changed
```
 src/frob/gates/__init__.py | 16 ++++++++++++++
 tests/test_gates.py        | 53 ++++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2549/ticket.md   |  9 ++++++--
 3 files changed, 76 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageGate::test_cov007_silent_for_a_strata_node_whose_clearance_is_not_public` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov007_still_fires_for_a_python_private_helper_after_t2549` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov007_flags_doc_anchor_on_private_helper` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov007_silent_for_doc_anchor_on_public_symbol` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2549/src/frob/app/ticket_runner/_verify.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2549, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md

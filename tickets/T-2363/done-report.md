## Done report

Changed: src/frob/__init__.py (documentation declaration only)

Decision: DECLARED, not structurally fixed. Measured (frob.check._python.
_build_import_graph + frob.cycle.graph.find_cycles against the real src/
tree, must-fail-fixture verified via the T-2358 planted-cycle regression
test) that the SCC T-2358 originally described as a 5-edge ring is a real,
live 160-node CYCLE001 error currently red on `frob check --only cycle`
(representative file src/frob/__init__.py). Re-measurement for T-2363 found
the SCC is actually WORSE than the original description: serve/_tools.py
carries a SECOND, independent module-level edge into frob.tickets
(`from frob.tickets import doable, load_queue`, line 24) that bypasses
frob.stats entirely -- so the smallest-looking candidate fix (cut
stats->tickets) would not have collapsed the cycle, which would have been
a silently-incomplete "fix" had I picked it without measuring first.

Five candidate edges to invert/extract were catalogued (full detail in
T-draft-4a262fb2's ticket body and the src/frob/__init__.py comment), each
touching a different package's public surface with no obviously-correct
choice from the measurement alone. Per the repo owner's standing
instruction on T-2358 ("if that decision is not obvious, stop and tell me
rather than guessing"), the direction pick is left to the owner via
T-draft-4a262fb2 rather than made unilaterally here.

Declaration mechanism: attempted `# frob:waive CYCLE001` at the
representative file first, per this repo's own documented convention
(CYCLE001 listed among waivable rules in src/frob/gates/_waive.py, T-2364's
comment there says the point of adding code=CYCLE001 was to make cycles
"waivable"). Verified with --no-cache that it does NOT suppress the
finding -- `frob check --only cycle`'s frob-cycle tool never calls into
the waiver pipeline at all (grepped both src/frob/check/__init__.py and
_python.py for "waive": zero hits; _apply_waivers only consumes Violation
objects from the separate frob.gates rule pipeline). Filed this gap
separately (T-draft-f5281af2, scope src/frob/check/**, src/frob/gates/**
-- outside T-2363's own scope) rather than fixing it under this ticket.
Replaced the inert frob:waive with a plain (non-DSL) documentation comment
so the declaration doesn't misrepresent itself as a working suppression;
CYCLE001 remains a live, unwaived `frob check` error (unchanged from
before this ticket -- not a regression, a pre-existing state now
documented and root-caused instead of silently unowned).

Evidence: tests/unit/test_capability_and_deploy_cycle_regression.py::
TestPlantedCycleStillDetected::test_planted_two_node_cycle_is_detected
(positive control: repo's own cycle detector still catches a planted
cycle after this change -- ran green, 3 passed, exitstatus=0). No
fix-behavior test exists to bind since this ticket declares rather than
changes cycle-detection outcomes.

Filed:
- T-draft-4a262fb2 -- owner decision on which of the 5 edges to
  invert/extract to actually break the 160-node cycle.
- T-draft-f5281af2 -- CYCLE001 findings never pass through the waiver
  pipeline (frob:waive CYCLE001 is silently inert); found while
  attempting the declaration mechanism for this ticket.

Gates: `frob check --only cycle` still reports the pre-existing CYCLE001
error at src/frob/__init__.py (expected -- declared, not fixed; not a
regression, same error present before this ticket touched anything).
`frob cycle src/frob` (the CLI command, distinct from the gate's own
`_build_import_graph`/`find_cycles` pipeline) reports "no cycles found"
on the same tree where the gate pipeline finds 7 cycles including this
160-node one -- a second, separate detector-fidelity gap not fixed here
(matches this repo's known prior-art pattern of `frob cycle` missing
cycles a src-layout gate catches; not filed as a new ticket since it is
the same known class of issue, not a new discovery, and is out of this
ticket's declared scope).

### Changed
```
 tickets/T-2363/ticket.md           | 17 +++++++++++++-
 tickets/T-draft-4a262fb2/ticket.md | 45 ++++++++++++++++++++++++++++++++++++++
 tickets/T-draft-f5281af2/ticket.md | 38 ++++++++++++++++++++++++++++++++
 3 files changed, 99 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_capability_and_deploy_cycle_regression.py::TestPlantedCycleStillDetected::test_planted_two_node_cycle_is_detected` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2561/ticket.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2363/src/frob/app/ticket_runner/_ledger_mirror.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2363/src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2363/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2363, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md

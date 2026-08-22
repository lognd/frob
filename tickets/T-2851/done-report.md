## Done report

Verified the seam and every land-critical call site before splitting, per
the ticket's own caution that `bug_repro_outcome_at_ref` is load-bearing.

Seam: confirmed real (TEST016/TEST018 + shared quoting helpers vs the
entire BUG002/must-still-pass family), matching the filing agent's claim,
with three small corrections found by measurement: (1) the BUG002 family
DOES call the shared quoting helpers `_quoted_char_ranges`/`_is_quoted`
(3 call sites each, inside `_bug002_waiver_reason`/
`_no_behavior_change_reason`/`_must_still_pass_controls`) -- not "zero
shared calls" as filed, though this is a normal cross-module dependency,
not a coupling problem; (2) two BUG002-only module constants
(`_BUG_REPRO_TIMEOUT_S`, `_BUG_REPRO_WORKTREE_TIMEOUT_S`) and three
BUG002-only compiled regexes (`_BUG002_WAIVER_RE`, `_NO_BEHAVIOR_CHANGE_RE`,
`_MUST_STILL_PASS_RE`) had to move with the family (missed on a first
line-range-only extraction, caught immediately by `import frob.gates`
failing with NameError); (3) `_ERROR_KINDS` (used by both TEST016's
severity computation and BUG002's kind-gate check) is a genuinely shared
one-line constant -- kept in `_mutation_evidence.py`, imported locally
inside `bug_repro_violations` (not at module level) specifically to avoid
a circular import, since `_mutation_evidence.py` also imports the public
BUG002 names back from the new module at its own bottom.

THE LAND-CRITICAL HAZARD (found by grep, confirmed by running the real
test files, exactly per this session's own "import retarget invalidates
patch targets" lesson): 40 `mock.patch("frob.gates._mutation_evidence.
_bug_repro_outcome_at_ref"/"_run_designated_test", ...)` call sites across
5 test files patch these PRIVATE names by full string path. Moving the
whole family into one new module means the internal call from
`bug_repro_violations`/`must_still_pass_violations` to
`_bug_repro_outcome_at_ref` now resolves in the NEW module's own globals,
not `_mutation_evidence`'s -- patching the OLD path would silently stop
intercepting and let REAL git-worktree-checkout + subprocess-pytest-run
code fire during what are meant to be fast, isolated unit tests. Fixed by
rewriting all 40 patch-target strings (plus 7 direct `from frob.gates.
_mutation_evidence import _BugReproOutcome/_BUG_REPRO_TIMEOUT_S/
_no_behavior_change_reason/...` statements) to point at
`frob.gates._bug_repro`, in the same diff, then verified with a positive
control: reverted one patch target back to the old path and confirmed the
test fails LOUDLY (AttributeError / ImportError), not silently -- proving
the fix is load-bearing, not cosmetic.

Public API preserved with zero external call-site changes: `bug_repro_
outcome_at_ref`, `bug_repro_violations`, `designated_repro_test`, `must_
still_pass_violations`, `BugReproOutcome` are re-exported from `frob.gates.
_mutation_evidence` (bottom-of-file import), so `frob.gates.__init__`'s
existing `from frob.gates._mutation_evidence import (...)` -- and every
caller that goes through `frob.gates` or `frob.tickets._land`/`frob.app.
ticket_runner._close_cmd`/`_verify` -- needed zero changes. Verified both
import orders are circular-import-safe (`import frob.gates` and a direct
`import frob.gates._bug_repro` first, standalone).

`_mutation_evidence.py` dropped 1281 -> 408 lines, under LARGE001's
500-line threshold on its own -- self-closing, its stale LARGE001 waiver
removed (replaced with a plain comment pointing at the actual T-2851
land). `_bug_repro.py` is 938 lines, still over threshold -- given a
FRESH T-1651-grade waiver reasoned on its own post-split shape (one
checkout/spawn/classify pipeline behind a single shared classifier, with
exactly two consumers -- BUG002/BUG003 -- that call it rather than
duplicating it; splitting further would sever that call chain, not find
an independent consumer set), not the filing ticket's original
"deferred, land-critical" reasoning (that reasoning was for NOT touching
it in a batch, not a property of the post-split file).

Verification:
- `import frob.gates` and standalone `import frob.gates._bug_repro`: both
  clean, no circular-import error.
- Full affected test set (96 tests): tests/gates/test_bug_repro_at_ref_public.py,
  tests/test_bug002_no_behavior_change.py, tests/test_gates_mutation_evidence.py,
  tests/unit/test_ticket_close_bug002_t1427.py,
  tests/unit/test_ticket_runner_designate_repro.py,
  tests/unit/test_ticket_close_bug002_t1438.py -- 96 passed, 0 failed.
- Land-adjacent suites: tests/unit/test_ticket_land_bug003_t2215.py,
  tests/unit/test_land_already_landed.py,
  tests/unit/test_land_finish_idempotent.py -- 29 passed, 0 failed.
- Positive control: reverted one patch target to the OLD (now-wrong)
  module path -- test failed loudly (AttributeError), confirming the
  rewrite is load-bearing, not vacuous. Restored, re-verified green.
- arch_gate()+_apply_waivers() against a live build_graph() snapshot
  (committed tree): `_mutation_evidence.py` produces zero findings;
  `_bug_repro.py`'s LARGE001 is WAIVED; no KEPT findings from either file.
- `tests/test_gates.py`'s full run has 6 pre-existing failures
  (TestWireGate, TestFixEngineTierABatch2, TestAutofixManifest,
  TestKnownGateRuleIds, TestDoc004ConsoleCommandDrift, TestOptInGates) --
  confirmed unrelated by reproducing the identical 6 failures from the
  PRIMARY /home/logan/projects/frob checkout (unmodified main), before
  touching this worktree's own copy.

Changed: src/frob/gates/_mutation_evidence.py (BUG002 family removed,
  stale LARGE001 waiver removed), src/frob/gates/_bug_repro.py (new,
  fresh LARGE001 waiver), tests/gates/test_bug_repro_at_ref_public.py,
  tests/test_bug002_no_behavior_change.py,
  tests/test_gates_mutation_evidence.py,
  tests/unit/test_ticket_close_bug002_t1427.py,
  tests/unit/test_ticket_runner_designate_repro.py (patch-target/import
  path rewrites, no logic changes)
Evidence: tests/gates/test_bug_repro_at_ref_public.py::TestBugReproOutcomeAtRefPublic::test_wraps_the_private_classifier,
  tests/test_gates_mutation_evidence.py::TestBugReproViolations::test_failed_at_parent_no_violation,
  tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent::test_refuses_passed_at_parent
Filed: none
Gates: arch_gate()+_apply_waivers() clean for both files (LARGE001 waived
  on _bug_repro.py, zero findings on _mutation_evidence.py); no double
  quotes in either waiver reason string

### Changed
```
 src/frob/gates/_bug_repro.py                     | 956 +++++++++++++++++++++++
 src/frob/gates/_mutation_evidence.py             | 903 +--------------------
 tests/gates/test_bug_repro_at_ref_public.py      |   6 +-
 tests/test_bug002_no_behavior_change.py          |   8 +-
 tests/test_gates_mutation_evidence.py            |  56 +-
 tests/unit/test_ticket_close_bug002_t1427.py     |   8 +-
 tests/unit/test_ticket_runner_designate_repro.py |  26 +-
 tickets/T-2851/ticket.md                         |  10 +-
 8 files changed, 1032 insertions(+), 941 deletions(-)
```

### Evidence
- `tests/gates/test_bug_repro_at_ref_public.py::TestBugReproOutcomeAtRefPublic::test_wraps_the_private_classifier` (pytest node id, verified passing when recorded)
- `tests/test_gates_mutation_evidence.py::TestBugReproViolations::test_failed_at_parent_no_violation` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent::test_refuses_passed_at_parent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 52 error(s), 530 warning(s), 794 waived
- error-findings: AFFECT001@src/frob/gates/_bug_repro.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@frob-core/src/callgraph.rs, COV001@frob-core/src/exact_regions.rs, COV001@frob-core/src/lib.rs, COV001@frob-core/src/r3.rs, COV001@frob-core/src/r4.rs, COV001@frob-core/src/r5.rs, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC006@docs/modules/dup-sota-survey.md, DOC006@docs/modules/dup.md, DOC006@docs/modules/graph.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/dup.md, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@docs/modules/tickets-landing.md, DRIFT002@frob-core/src/lib.rs, DRIFT002@tests/test_arch_near_duplicate_native.py, DRIFT002@tests/unit/test_dup_core.py, DSL001@tests/unit/test_coordinator_scripts.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2851/src/frob/gates/_bug_repro.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2851/src/frob/gates/_mutation_evidence.py, F822@/home/logan/projects/frob/.claude/worktrees/t-2851/src/frob/gates/_bug_repro.py, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2851, REF001@frob-core/src/callgraph.rs, REF001@frob-core/src/exact_regions.rs, REF001@frob-core/src/r3.rs, REF001@frob-core/src/r4.rs, REF001@frob-core/src/r5.rs, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@frob-core/src/exact_regions.rs, TEST001@frob-core/src/lib.rs, TEST001@frob-core/src/r3.rs, TEST001@frob-core/src/r4.rs, TEST001@frob-core/src/r5.rs, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md

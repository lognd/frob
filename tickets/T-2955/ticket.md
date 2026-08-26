---
id: T-2955
title: 'frob-dup: triage tests/ duplicate cluster (~490 groups)'
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: T-2378
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-2955/**
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets/T-2955/**
  reason: documenting the detector-narrowing triage decision; no production code change
    in this ticket
  actor: logan
  at: '2026-08-26'
body_changes:
- mode: append
  reason: record the triage decision (detector-narrowing, evidenced, not blanket exclusion
    or 479 waivers) and the filed follow-up ticket
  actor: logan
  at: '2026-08-26'
  old_length: 2053
  new_length: 7202
- mode: append
  reason: 'BUG002 needs an explicit no-behavior-change declaration: this ticket is
    a triage/decision record with no code change'
  actor: logan
  at: '2026-08-26'
  old_length: 7201
  new_length: 7406
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
acceptance:
- text: given the tests/ frob-dup cluster measured in this ticket's body, when triaged,
    then a decision (extract / per-group waive / detector-narrowing proposal) is recorded
    for every sub-cluster, decomposed into further children as needed
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 5f049a541dc3273cd7dad69fcdd277fe0ed4c021
---
Filed as a T-2378 sibling per the "decompose, do not mega-land" instruction.

Cluster (frob-dup, unscoped, measured 2026-08-26): the test-suite is by far
the largest share of both exact and renamed findings -- roughly 490 of the
557 unaccounted groups have EVERY fragment inside tests/. Rough per-file
breakdown (dominant files): tests/unit/strata (76), tests/test_gates.py
(50), tests/test_vet.py (23), tests/unit/test_arch.py (16),
tests/test_docptr_gate.py (15), tests/unit/perf (10),
tests/test_pii_structural_gate.py (10), tests/test_graph.py (10),
tests/unit/graph (9), tests/test_dup.py (7), plus a long tail of 3-6-count
groups across dozens of other test files (see the tool's frob-dup output
for the full list).

Per the parent ticket's own instruction #2: "Test fixtures that
deliberately repeat a shape for readability are not debt." A first pass at
several of these (arrange-block boilerplate: tmp_path setup, a small
parametrized helper, a shared assertion shape) strongly suggests most of
this cluster is exactly that -- deliberate repetition for per-test
readability, not desync risk, since each test's fixture is read and
maintained in isolation.

This ticket is NOT pre-decided extract vs waive vs narrow-detector. Given
the volume, the likely right shape is: (a) spot-check a sample of the
larger groups (tests/unit/strata's 76, tests/test_gates.py's 50) for any
GENUINE shared-logic case masquerading as "just a test", extract those; (b)
for the rest, propose either a `frob:waive DUP001/DUP002` per group with a
real per-group reason (slow, hundreds of groups), OR a detector-level
change (narrow frob-dup to exclude tests/ entirely, or raise its
size/severity threshold for files under tests/) -- the latter needs a
deliberate decision from whoever owns frob-dup's design, so raise it
explicitly rather than waiving hundreds individually. Decompose further by
directory before dispatching.

Re-measure via: uv run frob check --json --only static, filter
tool=="frob-dup", filter messages where every location starts with "tests/".


TRIAGE DECISION (T-2955, re-measured 2026-08-26 against main at
e66200238): unscoped frob-dup, tests/-only unaccounted groups = 479
(of 553 unscoped total, 5 waived). Directory breakdown essentially
unchanged from the parent's figures (tests/unit/strata, test_gates.py,
test_vet.py, unit/test_arch.py etc still dominate).

Spot-checked 4 of the largest/most-varied groups (not a full audit --
see residue below), deliberately picking across different directories
and shapes:

1. tests/unit/test_arch.py:428/785 and :478/844 (50-line, two
   separate groups): three near-identical synthetic fixture files
   (normalize_alpha/beta/gamma) written per-test to exercise arch's
   abstraction-opportunity detector, then a near-copy of that same
   3-function fixture reused in a DIFFERENT test proving init-reexport
   does NOT suppress the same finding. The near-duplication is the
   whole POINT of the fixture (arch's own detector needs genuinely
   near-duplicate bodies to fire) -- collapsing it into a shared
   helper would obscure exactly the signal each test is asserting on,
   and the two tests assert different things about the same shaped
   input. Verdict: deliberate repetition, not debt.

2. tests/unit/strata/test_litmus_waive.py:85 vs
   test_litmus_waive_store.py:82 (47-line): the node-target and
   store-target variants of the SAME litmus round (a waiver naming
   sub-target CWE-78 must not suppress CWE-89), each exercising a
   structurally distinct target kind (node vs derived-state store).
   This is the established "parallel litmus suite" shape (mirrored
   test files per target kind) already used throughout
   tests/unit/strata -- verdict: deliberate parallel-suite repetition,
   not debt (collapsing node/store variants into one shared body would
   make future litmus rounds add a conditional branch instead of a
   plain mirrored test, which is a worse trade for a test suite).

3. tests/test_gates.py:14767/14815 (47-line): two arrange-blocks
   building a tmp_path repo with a src/good.py fixture + tickets.md,
   asserting different things about WAIVE004 stale-waiver deletion
   under different pre-conditions. Standard arrange-block boilerplate,
   independent per-test setup -- deliberate repetition.

4. tests/test_dup.py:77/135/444/646/757 (49-line, 5 fragments): a
   recurring "build two near-clone source files + call find_duplicates"
   arrange block used across 5 different assertions about the dup
   pipeline itself -- SAME verdict, standard fixture-arrange
   repetition, and (given this is the dup module's OWN test file)
   collapsing it would make the dup test suite's own fixtures
   ironically the first thing DUP001 would need a self-referential
   waiver for.

DECISION: DETECTOR-NARROWING is the recommended disposition, not a
blanket exclusion and not 479 individual per-group waivers. Per-group
waivers at this volume would themselves become a form of debt (479
near-identical low-content `frob:waive` comments, each essentially
restating "this is a test fixture" -- worse maintenance burden than
the duplication itself). A blanket `tests/` exclusion is explicitly
rejected too: it would permanently blind frob-dup to real test-helper
duplication, which the parent ticket confirms exists elsewhere in this
same codebase's history (T-0375's own waiver-matching logic exists
because DUP001/DUP002 already catches real diff-scoped test clones).

RECOMMENDED narrowing (not implemented in this ticket -- real
detector-design work, see residue): frob-dup's unscoped scan
(`frob.dup._legacy.find_duplicates`, the R1/R2 renamed/exact detector
behind the "static" stage's frob-dup tool) should raise its
`min_lines` threshold specifically for paths under `tests/` (a
directory-scoped override alongside the existing repo-wide
`min_lines: int = 6` default in `frob.dup._legacy`), OR add a
fixture-shape heuristic (a function body that is >50% string-literal
construction, the `write_text(...)`/dict-literal arrange-block shape
seen in all 4 samples above) that both the exact and renamed detectors
already have enough AST information to recognize. Both need real
measurement against a sample of tests/ groups (a positive-control
check per the playbook's "positive control or it proves nothing" --
confirm the narrowed rule still catches a PLANTED real test-helper
duplicate) before landing, which this triage ticket did not have
budget to do safely.

NOT reached zero, and not expected to reach zero without the detector
change above. Filed the detector-narrowing implementation as its own
ticket rather than force either extreme (blanket exclusion or 479
waivers) under this ticket's triage-only scope.

Filed: T-2967 (frob-dup: narrow the tests/ renamed-detector threshold
or add a fixture-shape heuristic, with a positive-control check) --
carries the full recommendation above, the 4 spot-check samples as
its starting evidence, and the positive-control requirement.

T-2957 is NOT unblocked: this ticket's residue (479 groups) is the
large majority of the whole family's unaccounted count, and it
requires a real detector-design ticket (T-2967) to resolve honestly,
not a mechanical burn-down.

frob:no-behavior-change reason="this ticket records a triage decision (detector-narrowing, evidenced) in the ticket body only -- no production code changed, the detector-level fix is deferred to T-2967"
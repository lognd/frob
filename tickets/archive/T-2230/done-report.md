## Done report

Fixed the asymmetric omission: src/frob/gates/__init__.py re-exports
five names from frob.gates._mutation_evidence (BugReproOutcome,
bug_repro_outcome_at_ref, bug_repro_violations, designated_repro_test,
mutation_evidence_violations) but not must_still_pass_violations
(BUG003, T-2193, wired into land/close by T-2215). Added it to both
the import block and __all__, alphabetically adjacent to its siblings
-- the ONE missing name, per the ticket's own explicit instruction not
to widen "for consistency" and not to `import *`.

Public surface before this ticket (frob.gates, mutation-evidence
family): BugReproOutcome, bug_repro_outcome_at_ref,
bug_repro_violations, designated_repro_test,
mutation_evidence_violations (5 names).
After: the same 5 plus must_still_pass_violations (6 names). No other
name from _mutation_evidence became importable -- verified directly
(test_no_private_helper_becomes_importable checks 7 known private
names, including the regexes/helper T-2218 added earlier today, stay
absent from frob.gates).

CRITERION 3 (explicit call, as required): UPDATED the landed deep-
import call site. src/frob/tickets/_land.py's
_must_still_pass_land_violations did `from frob.gates._mutation_
evidence import must_still_pass_violations` with a comment explaining
the T-2218-labeled gap this ticket closes (the comment cited "T-2218"
-- a pre-existing mislabel from before this ticket existed as a
separate id; corrected in the same edit). Changed to
`from frob.gates import must_still_pass_violations`. This is the
ticket's own headline consequence ("already paid for once in landed
code") -- leaving it unfixed while adding the re-export would still
mean the fix accomplishes nothing for the one real consumer that
motivated filing it.

CONSEQUENCE OF THE CALL-SITE CHANGE, found and fixed: 4 of
tests/unit/test_ticket_land_bug003_t2215.py's tests patched
"frob.gates._mutation_evidence.must_still_pass_violations" via
unittest.mock.patch -- a name binding on the _mutation_evidence
submodule. Once _land.py's lazy import reads from frob.gates (the
package) instead, that package's own must_still_pass_violations
attribute (bound once, at frob.gates's own first-import time, to the
same function object) is what the local `from frob.gates import ...`
statement re-reads on every call -- patching the submodule's attribute
no longer reaches it (mock.patch's own "patch where it's looked up"
rule). Rebound all 6 patch-target strings in that file to
"frob.gates.must_still_pass_violations". Scope widened to include this
test file (frob ticket scope --add, reasoned) since fixing them is a
direct, mechanical consequence of criterion 3's own required change,
not unrelated work.

Repro: tests/test_gates.py::TestMutationEvidencePackageReexports::
test_must_still_pass_violations_importable_from_package. --check-repro
DOES fit this cleanly (an ImportError raised inside the test body is a
genuine pytest failure, not a forced fit) -- committed alone, watched
FAIL against pre-fix code with a real ImportError
("cannot import name 'must_still_pass_violations' from 'frob.gates'").
Fix committed separately.

Must-still-pass control (criterion 2, explicit in the ticket):
test_existing_sibling_reexports_still_resolve imports all five
pre-existing names from frob.gates and asserts each still resolves --
a rewritten/reordered import block silently dropping one would satisfy
the main criterion while breaking real consumers. Passes.

Criterion 4 control: test_no_private_helper_becomes_importable checks
7 known private _mutation_evidence names (the three quoting-related
ones T-2218 added earlier today, plus the three directive regexes,
plus one waiver-reason helper) stay unreachable from frob.gates.
Passes.

Verification:
- pytest tests/test_gates.py -k TestMutationEvidencePackageReexports
  -o addopts="" -q: 3 passed (0 pre-fix: 1 failed with the exact
  ImportError, 2 controls already passed unmodified).
- pytest tests/unit/test_ticket_land_bug003_t2215.py -o addopts=""
  -q: 10 passed, 0 failed (4 genuinely failed before the patch-target
  fix, confirming the mock-scope consequence was real, not
  hypothetical).
- frob test --base main: python exit=0, 7 outcomes recorded, all
  green.
- frob check --only lint --json: ty clean; the one ruff-check hit in
  a touched file (tests/test_gates.py:10, I001 import-sort) is a
  WARNING, pre-existing import-block drift, not introduced by this
  ticket's own added imports (auto-fixed by land's Tier-A absorption
  per the playbook).
- frob check --only cycle --json: unmoved at 3 errors, 1 warning
  (T-2202's tracked debt), diagnostics diffed line-for-line before and
  after -- the new lazy import inside _land.py's function body did not
  introduce or remove any reported cycle.

Gates: no error attributable to this ticket's own touched files
(src/frob/gates/__init__.py, src/frob/tickets/_land.py,
tests/test_gates.py, tests/unit/test_ticket_land_bug003_t2215.py).

### Changed
```
 src/frob/gates/__init__.py                  |  2 +
 src/frob/tickets/_land.py                   | 14 +++----
 tests/test_gates.py                         | 64 +++++++++++++++++++++++++++++
 tests/unit/test_ticket_land_bug003_t2215.py | 12 +++---
 tickets/T-2230/ticket.md                    | 42 ++++++++++++++++---
 5 files changed, 115 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestMutationEvidencePackageReexports::test_must_still_pass_violations_importable_from_package` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestMutationEvidencePackageReexports::test_existing_sibling_reexports_still_resolve` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_land_bug003_t2215.py::TestMustStillPassWiring::test_land_succeeds_when_gate_reports_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestMutationEvidencePackageReexports::test_no_private_helper_becomes_importable` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2230/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2230/tests/test_ticket_work_and_land_finish.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2230, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md

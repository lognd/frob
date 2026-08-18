---
id: T-2358
title: Three live import cycles in src/frob (deploy, vet, serve/stats), invisible
  to accounting because the cycle gate emits identity-less findings
state: done
kind: bug
origin: agent
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/deploy/_generate.py
- src/frob/deploy/_generate_windows.py
- src/frob/deploy/_generate_common.py
- src/frob/vet/_capability.py
- src/frob/vet/_capability_core.py
- src/frob/vet/_capability_scan.py
- tests/unit/deploy/test_generate.py
- tests/test_vet.py
- tests/test_vet_capability.py
- tests/test_capability_registry.py
- tests/unit/test_capability_and_deploy_cycle_regression.py
evidence_scope:
- tests/unit/test_capability_and_deploy_cycle_regression.py
- tests/unit/test_vet_cycle_regression.py
- tests/unit/deploy/test_generate.py
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/deploy/_generate.py
  reason: T-2358 was created with empty scope; adding the files actually touched,
    discovered when frob ticket land's out-of-scope waive-deletion check refused
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/deploy/_generate_windows.py
  reason: T-2358 was created with empty scope; adding the files actually touched,
    discovered when frob ticket land's out-of-scope waive-deletion check refused
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/deploy/_generate_common.py
  reason: T-2358 was created with empty scope; adding the files actually touched,
    discovered when frob ticket land's out-of-scope waive-deletion check refused
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/vet/_capability.py
  reason: T-2358 was created with empty scope; adding the files actually touched,
    discovered when frob ticket land's out-of-scope waive-deletion check refused
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/vet/_capability_core.py
  reason: T-2358 was created with empty scope; adding the files actually touched,
    discovered when frob ticket land's out-of-scope waive-deletion check refused
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/vet/_capability_scan.py
  reason: T-2358 was created with empty scope; adding the files actually touched,
    discovered when frob ticket land's out-of-scope waive-deletion check refused
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/deploy/test_generate.py
  reason: T-2358 was created with empty scope; adding the files actually touched,
    discovered when frob ticket land's out-of-scope waive-deletion check refused
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_vet.py
  reason: T-2358 was created with empty scope; adding the files actually touched,
    discovered when frob ticket land's out-of-scope waive-deletion check refused
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_vet_capability.py
  reason: T-2358 was created with empty scope; adding the files actually touched,
    discovered when frob ticket land's out-of-scope waive-deletion check refused
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_capability_registry.py
  reason: T-2358 was created with empty scope; adding the files actually touched,
    discovered when frob ticket land's out-of-scope waive-deletion check refused
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_capability_and_deploy_cycle_regression.py
  reason: T-2358 was created with empty scope; adding the files actually touched,
    discovered when frob ticket land's out-of-scope waive-deletion check refused
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_capability_and_deploy_cycle_regression.py::TestDeployAndCapabilityCycleRegression::test_generate_windows_no_longer_imports_generate
- tests/unit/test_capability_and_deploy_cycle_regression.py::TestDeployAndCapabilityCycleRegression::test_capability_scan_no_longer_imports_capability
- tests/unit/test_capability_and_deploy_cycle_regression.py::TestPlantedCycleStillDetected::test_planted_two_node_cycle_is_detected
- tests/unit/test_vet_cycle_regression.py::TestVetCycleRegression::test_vet_cluster_is_not_a_cycle
- tests/unit/deploy/test_generate.py::TestSorted::test_sorted
- tests/test_vet.py::TestCapabilityScan::test_scan_file_operations_names_registry_entry
designated_repro_test: tests/unit/test_capability_and_deploy_cycle_regression.py::TestDeployAndCapabilityCycleRegression::test_generate_windows_no_longer_imports_generate
acceptance:
- text: given src/frob, when frob cycle runs, then the deploy/_generate<->_generate_windows
    and vet/_capability<->_capability_scan cycles are gone (the 5-package serve/stats/tickets/testing/app
    cycle is escalated separately as T-2363, an architectural decision this ticket
    does not make implicitly)
  evidence:
  - tests/unit/test_capability_and_deploy_cycle_regression.py::TestDeployAndCapabilityCycleRegression::test_generate_windows_no_longer_imports_generate
  - tests/unit/test_capability_and_deploy_cycle_regression.py::TestDeployAndCapabilityCycleRegression::test_capability_scan_no_longer_imports_capability
- text: given a deliberately planted 2-node cycle, when the detector runs, then it
    is still reported (fix did not blind the detector)
  evidence:
  - tests/unit/test_capability_and_deploy_cycle_regression.py::TestPlantedCycleStillDetected::test_planted_two_node_cycle_is_detected
- text: given the touched packages, when their test suites run, then they pass
  evidence:
  - tests/unit/deploy/test_generate.py::TestSorted::test_sorted
  - tests/test_vet.py::TestCapabilityScan::test_scan_file_operations_names_registry_entry
acceptance_amendments:
- op: replace
  index: 0
  old_text: given src/frob, when frob cycle runs, then it reports zero import cycles
  new_text: given src/frob, when frob cycle runs, then the deploy/_generate<->_generate_windows
    and vet/_capability<->_capability_scan cycles are gone (the 5-package serve/stats/tickets/testing/app
    cycle is escalated separately as T-2363, an architectural decision this ticket
    does not make implicitly)
  reason: 'Investigation found the "zero cycles" criterion covers TWO structurally

    different problems: two isolated 2-module cycles (deploy, vet) that were

    genuinely fixable within this ticket''s own scope, and a 5-package

    cross-package strongly-connected component (serve/stats/tickets/testing/

    app, ~175 nodes) whose fix requires choosing which of five packages''

    dependency directions to invert -- an architectural call the brief

    explicitly said to escalate rather than guess at ("if that decision is

    not obvious, stop and tell me rather than guessing; I would rather own

    that call than have it made implicitly"). Narrowing this criterion to

    the two cycles actually fixed here, and filing the pentagon as its own

    ticket (T-2363) with the exact edge chain measured, keeps this ticket''s

    acceptance honest about what it delivered rather than forcing a false

    "zero cycles" claim or leaving the criterion permanently unbound.

    '
  actor: logan
  at: '2026-08-17'
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-17. `uv run frob cycle src/frob` reports three genuine
import cycles in this package:

  1. src/frob/deploy/_generate_windows.py <-> src/frob/deploy/_generate.py
  2. src/frob/vet/_capability_scan.py    <-> src/frob/vet/_capability.py
  3. src/frob/serve/_socketd.py -> src/frob/serve/_events.py
       -> src/frob/stats/__init__.py -> src/frob/serve/_to... (multi-node)

The third is reported by `frob check --only cycle` as a hard ERROR.

WHY THESE WENT UNNOTICED, WHICH IS THE INTERESTING PART: the cycle gate emits
its finding as

    frob-cycle:None None:None | import cycle: ...

-- `code=None`, `file=None`, the whole description in free text. So the
finding has NO IDENTITY. It cannot be attributed to a commit, owned by a
ticket, waived, counted in a floor comparison, or filed by the sweep. It has
presumably been sitting in the error floor unowned for a long time, visible
only to someone reading raw gate output rather than the accounting layer.

That identity-less shape is also the exact record that pinned the verify
quarantine and deadlocked the fleet for two hours today: `_verify.py::
_parse_error_findings_from_json` turned `(code or "", file or "")` into a
real `("", "")` identity. T-2313 patched the downstream choke point and
T-2345 fixed the parse boundary -- and T-2345's investigation is how this
producer was finally identified. The identity bug was MASKING a real
architectural defect.

REQUIRED: break all three cycles. These are structural, not cosmetic --
a cycle means two modules cannot be reasoned about, tested, or imported
independently, and it is the kind of thing that turns into an import-order
heisenbug later.
 - The two 2-node cycles are likely a shared helper wanting its own module,
   or a type-only import that belongs under `TYPE_CHECKING`.
 - The serve/stats cycle spans package boundaries and needs a real look at
   which direction the dependency SHOULD run; do not break it by moving an
   import inside a function just to silence the detector. That hides the
   cycle from the tool while leaving the coupling in place.

POSITIVE CONTROLS: (1) `frob cycle src/frob` reports zero cycles afterward;
(2) must-still-pass -- a deliberately planted 2-node cycle IS still detected,
so the fix did not simply blind the detector (this repo has already been
burned once by a "clean" cycle verdict that came from a detector that could
not see the planted case); (3) the full test suite for the touched packages
passes, since breaking a cycle usually means moving symbols.
---
id: T-2550
title: 'COV006: all 18 live findings are call-graph blindness (cross-file public entry,
  test-helper indirection), not unexercised bindings'
state: in-progress
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/__init__.py
- tests/test_vet.py
- tests/test_lang.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_vet.py
  reason: trace 1 fix lives in gates/__init__.py (already scoped); trace 2/3 findings
    require touching the three test files that pin/waive the COV006 misclassifications
    the traces identified
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_lang.py
  reason: trace 1 fix lives in gates/__init__.py (already scoped); trace 2/3 findings
    require touching the three test files that pin/waive the COV006 misclassifications
    the traces identified
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_ticket_land.py
  reason: trace 1 fix lives in gates/__init__.py (already scoped); trace 2/3 findings
    require touching the three test files that pin/waive the COV006 misclassifications
    the traces identified
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: tests/unit/test_vet.py
  reason: 'corrected path: tests live directly under tests/, not tests/unit/'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: tests/unit/test_lang.py
  reason: 'corrected path: tests live directly under tests/, not tests/unit/'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: tests/unit/test_ticket_land.py
  reason: 'corrected path: tests live directly under tests/, not tests/unit/'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_vet.py
  reason: 'corrected path: tests live directly under tests/, not tests/unit/'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_lang.py
  reason: 'corrected path: tests live directly under tests/, not tests/unit/'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'corrected path: tests live directly under tests/, not tests/unit/'
  actor: logan
  at: '2026-08-18'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
All 18 live COV006 findings measured today are the gate being wrong, not
a test failing to exercise its bound symbol. Verified by reading every
one of the 18 test bodies (tests/test_lang.py 6, tests/test_ticket_land.py
6, tests/test_vet.py 6).

MECHANISM. `_cov006` is built on `frob.graph.callgraph.build_call_graph`,
which by construction NEVER records an edge into a PUBLIC callee (its
docstring says so; that behavior is load-bearing for dup/perf, T-0288/
T-0290). `_cov006` compensates with `_cov006_public_wrapper_reachable`,
but that rescue only covers ONE shape: a public wrapper in the SAME FILE
as the target, called BY NAME from the test's own body. Every one of the
18 findings sits outside that shape, in two sub-classes:

(a) The test reaches the private target through a public entry point in a
    DIFFERENT file / package re-export, several hops out. Examples:
    tests/test_vet.py::TestCapabilityScan.test_public_sibling_wrapper_
    exec_is_resolved_one_hop calls `frob.vet._capability.scan_file_
    capabilities`, which reaches `_capability_python.py::_python_local_
    wrapper_capabilities`; every tests/test_ticket_land.py finding drives
    the full `land()` pipeline down to a `_land_git_ops`/`_land_squash`
    helper.

(b) The test calls the public entry from a TEST-CLASS HELPER METHOD, not
    from the test body, so even the same-file lookahead's "called by name
    from the test's own body" condition cannot match. All six
    tests/test_lang.py findings are this: TestFromImportSubmodule
    Resolution's own `_resolve_all` helper calls `extract_imports` /
    `resolve_local_import`, and the class docstring states outright that
    the tests deliberately drive the real two-hop pipeline rather than
    re-asserting on `_python_import_specifiers` in isolation.

CONSEQUENCE FOR T-2370's PROMOTION HALF: COV006 must NOT be promoted from
WARN to ERROR while this holds. Its own docstring already says WARN is
deliberate because the resolver is "explicitly best-effort, name-based"
-- and this repo has already been burned once by a rule-level soundness
assumption over that same graph (the callgraph-resolves-by-bare-short-name
incident). A promotion here would red the floor with 18 findings that are
all false.

POSSIBLE FIXES (owner decision, not assumed here):
- extend the rescue to a public entry point in ANY file, not just the
  target's own file (widens the parse cost);
- follow calls made from helper methods defined on the test's own class;
- or accept that COV006 is advisory-only and drop the promotion half of
  its acceptance criteria for this code specifically.

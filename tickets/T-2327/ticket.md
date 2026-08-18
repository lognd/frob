---
id: T-2327
title: 'DOC012 promotion: update stale WARN assertion in tests/test_gates.py'
state: done
kind: docs
origin: human
created: '2026-08-17'
priority: medium
parent: T-2299
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: retry lease check
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_gates.py::TestDoc012CommandSectionGate::test_undocumented_subcommand_fails
designated_repro_test: null
acceptance:
- text: given tests/test_gates.py::TestDoc012CommandSectionGate.test_undocumented_subcommand_fails,
    when read, then it asserts Severity.ERROR not Severity.WARN
  evidence:
  - tests/test_gates.py::TestDoc012CommandSectionGate::test_undocumented_subcommand_fails
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2299 promoted DOC012 (docs/modules/gates.md's "DOC012 dedicated
command-section drift-lock" section, src/frob/gates/_docblocks.py::
_doc012_violation) from WARN to ERROR now that the disclosed T-1783
backlog measures zero.

tests/test_gates.py::TestDoc012CommandSectionGate.test_undocumented_
subcommand_fails still asserts `v.severity == Severity.WARN` -- stale
after the promotion. T-2299 could not fix this directly because
tests/test_gates.py carried a live cross-worktree lease (T-2314) at
promotion time, so the must-fail fixture proving the new severity was
added in a new, disjoint file instead
(tests/test_doc012_promotion.py::TestDoc012PromotedToError).

REQUIRED: once T-2314 (or whichever ticket currently holds
tests/test_gates.py) is no longer live, update
test_undocumented_subcommand_fails's assertion to
`Severity.ERROR`, and consider folding
tests/test_doc012_promotion.py's fixture back into
TestDoc012CommandSectionGate to remove the duplication.
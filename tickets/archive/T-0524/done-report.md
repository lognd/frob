## Done report

Measured 128 COV007 findings repo-wide via `frob check --only coverage`
on this worktree. Triaged and dispositioned 36 across 5 batches, each
committed separately:

1. src/frob/tickets/__init__.py (10 findings): 9 redundant frob:doc
   directives removed from private helpers whose public entrypoint
   (leased_by, scope_breadth_context, has_substantive_done_report via the
   thin _has_done_report wrapper) already carries the same anchor; 1
   waived (_allocate_ticket_id's decision-record anchor genuinely
   documents its own allocation algorithm/design rationale, T-0162, not
   the public API surface).
2. src/frob/lang/_common.py (7 findings): all 7 waived --
   docs/modules/lang.md's Primitives section is a deliberate,
   per-function architecture doc of this module's internal tree-sitter
   helpers, each getting its own named bullet by design.
3. src/frob/dup/_core.py (7 findings): all 7 waived --
   docs/modules/dup.md individually frob:describes each private
   frob_core shim by name across its Rust-core/rung-r4/R1.5/rung-r5
   sections.
4. src/frob/vet/_capability_registry.py (6 findings): 5 redundant
   directives removed (already covered by the public
   DANGEROUS_OPERATIONS/CAPABILITY_MATRIX_EXCUSES constants and the
   capability_matrix function these private schema classes/helpers feed);
   1 waived (_validate_registry_kinds is a standalone drift-lock helper
   with no public wrapper, called directly by its own tests).
5. src/frob/gates/__init__.py (6 findings): 2 redundant directives
   removed (_severity_overrides/_anchor_mismatch_message, already covered
   by run_gates/docanchor_gate); 4 waived
   (_file_has_reasoned_doc_waiver/_inv003_doc_violations/
   _markdown_sections/_inv004_doc_violations are individually walked
   through by docs/modules/gates.md's Invariants section, a deliberate
   architecture doc of the INV003/INV004 design).

Verified post-fix: `frob check --only coverage` COV007 unwaived count
dropped from 128 to 92, confirmed by direct grep-count on the fresh check
output (128 - 36 = 92).

The remaining 92 findings span 43 files, none yet triaged in this pass.
Given the volume, not filed T-draft-9cd762ad (never refiled) (renumbers on merge to main) as
a continuation ticket with the exact per-file finding-count breakdown and
the same disposition policy (move/waive/demote, batch by module, commit
per batch) T-0524's own batches established -- this is the honest
remainder the dispatch's own target line explicitly allows ("0 unwaived
COV006/COV007 or a filed calibration ticket for the honest remainder with
exact counts").

Ran the full test suites for every module touched (tickets, lang, dup,
capability_registry/vet, gates) after each batch -- all green, no
regressions. `frob check --ticket T-0524 --base <pre-work commit>` is
clean (0 errors, 0 warnings, 0 waived beyond the intended COV007
waivers) for this ticket's own scoped diff.

### Changed
```
 src/frob/dup/_core.py                |  28 +++
 src/frob/gates/__init__.py           |  44 +++-
 src/frob/lang/_common.py             |  28 +++
 src/frob/strata/_waive.py            |   6 +-
 src/frob/tickets/__init__.py         |  42 +++-
 src/frob/tickets/_models.py          |  25 ++-
 src/frob/vet/_capability_registry.py |  20 +-
 tests/system/test_cli_check.py       |   7 +-
 tests/test_gates.py                  |  19 ++
 tests/test_tickets.py                |   9 +
 tests/unit/test_check.py             |   5 +-
 tickets.md                           | 397 ++++++++++++++++++++++++++++++++++-
 12 files changed, 597 insertions(+), 33 deletions(-)
```

### Evidence
- `tests/test_tickets_lease.py::TestBreadthPerf::test_computed_once_per_doable_call` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestValidateRegistryKinds::test_known_kinds_pass` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv003Gate::test_illustrative_example_reason_does_not_self_waive` (pytest node id, verified passing when recorded)

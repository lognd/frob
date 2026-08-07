---
id: T-0529
title: 'COV007 burndown continuation: 92 residual findings across 43 files'
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov005_directive_rebound_to_private_symbol_flags
- tests/test_gates.py::TestCoverageGate::test_cov005_same_symbol_no_rebind_is_clean
- tests/test_gates.py::TestCoverageGate::test_cov005_no_old_blob_is_clean
designated_repro_test: null
threat: null
component: null
---
T-0524 measured 128 COV007 findings repo-wide (`frob check --only
coverage`, this worktree). Triaged and dispositioned 36 across 5 batches
(each committed separately):

- `src/frob/tickets/__init__.py` (10): 9 redundant `frob:doc` directives
  removed (already covered by the public entrypoint they feed --
  `leased_by`, `scope_breadth_context`, `has_substantive_done_report`);
  1 waived (`_allocate_ticket_id`'s decision-record anchor documents its
  own algorithm, not a public-API surface).
- `src/frob/lang/_common.py` (7): all 7 waived -- docs/modules/lang.md's
  "Primitives" section is a deliberate, per-function architecture doc of
  this module's internal tree-sitter helpers, individually named by
  bullet.
- `src/frob/dup/_core.py` (7): all 7 waived -- docs/modules/dup.md
  individually `frob:describes` each private frob_core shim by name
  across its Rust-core/rung-r4/R1.5/rung-r5 sections.
- `src/frob/vet/_capability_registry.py` (6): 5 redundant directives
  removed (already covered by `DANGEROUS_OPERATIONS`/
  `CAPABILITY_MATRIX_EXCUSES`/`capability_matrix`, the public constants/
  function these private schema classes and helpers feed); 1 waived
  (`_validate_registry_kinds` is a standalone drift-lock helper with no
  public wrapper, called directly by its own tests).
- `src/frob/gates/__init__.py` (6): 2 redundant directives removed
  (`_severity_overrides`/`_anchor_mismatch_message`, already covered by
  `run_gates`/`docanchor_gate`); 4 waived (`_file_has_reasoned_doc_waiver`/
  `_inv003_doc_violations`/`_markdown_sections`/`_inv004_doc_violations`
  are individually walked through by docs/modules/gates.md's Invariants
  section, a deliberate architecture doc of the INV003/INV004 design).

The remaining 92 findings (measured via a fresh `frob check --only
coverage` after all 5 batches landed) span 43 files, none yet triaged:

```
5 src/frob/vet/_obfuscation.py
5 src/frob/vet/_capability.py
5 src/frob/tickets/_store.py
5 src/frob/strata/_claims.py
4 src/frob/vet/_source.py
4 src/frob/tickets/_models.py
4 src/frob/strata/_plan.py
3 src/frob/vet/_lockfile.py
3 src/frob/vet/_ecosystem.py
3 src/frob/testing/_runners.py
3 src/frob/strata/_waive.py
3 src/frob/strata/_ast.py
3 src/frob/graph/digest.py
3 src/frob/gates/_prework.py
2 src/frob/vet/_typosquat.py
2 src/frob/vet/_registry.py
2 src/frob/vet/_osv.py
2 src/frob/vet/_cache.py
2 src/frob/strata/_threat.py
2 src/frob/strata/_selfconform.py
2 src/frob/gates/_secrets.py
2 src/frob/excludes.py
2 src/frob/check/_python.py
1 src/frob/vet/_models.py
1 src/frob/vet/_lifecycle.py
1 src/frob/vet/_containment.py
1 src/frob/vet/_allow.py
1 src/frob/tickets/_reconcile.py
1 src/frob/tickets/_land.py
1 src/frob/strata/_krb.py
1 src/frob/strata/_host.py
1 src/frob/strata/_facts.py
1 src/frob/strata/_code_binding.py
1 src/frob/logging/formatter.py
1 src/frob/logging/filter.py
1 src/frob/lang/_walk_python.py
1 src/frob/lang/__init__.py
1 src/frob/graph/dsl.py
1 src/frob/gates/invariants.py
1 src/frob/gates/decisions.py
1 src/frob/gates/_pii_structural.py
1 src/frob/dup/_pipeline.py
1 src/frob/dup/_cache.py
1 src/frob/app/check_runner.py
```

The same three dispositions from T-0524's batches apply per finding:
move the `frob:doc` edge to the public caller/constant that already (or
should) carry it, waive with a specific reason when the private symbol
genuinely is a deliberately-documented internal contract (an
architecture-doc section individually naming private helpers, a
standalone drift-lock/decision-record anchor with no public wrapper), or
demote/reword a stale reference. Batch by module, commit per batch, same
as T-0524's pattern -- this ticket exists so the residual gets the same
per-finding triage rather than being silently left unaccounted for.
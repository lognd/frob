---
id: T-0951
title: 'archgate/pii_structural rust-candidate feasibility: find a compute-only kernel
  boundary or dispose honestly'
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: T-0927
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- src/frob/gates/_pii_structural.py
- docs/audits/check-performance.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/audits/check-performance.md
  reason: dispatch instruction explicitly asked for a decision document appended to
    docs/audits/check-performance.md as the ticket deliverable
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/test_arch.py::TestAbstractionOpportunityDiscriminators::test_generic_signature_near_duplicate_bodies_still_flagged
- tests/test_pii_structural_gate.py::TestFieldNames::test_password_field_fires
designated_repro_test: null
threat: null
component: null
---
Found while working T-0930 (rust-candidate row migration off the
frob-check-performance audit, docs/audits/check-performance.md). Two of
the audit's four rust-candidate rows -- archgate (row 3, 11.08s) and
pii_structural (row 7, 4.60s) -- were investigated only at a read-level
this pass (not attempted). Both are dominated by tree-sitter Node/
semantic-analysis code (SOLID/LSP/type-design checks for archgate;
class-field-name/type-annotation/AST-shaped scanning for
pii_structural's 1954-line module), NOT the plain "serialized token
list in, data out" shape frob_core's existing kernels (frob.dup._core,
and T-0930's own dead_symbols investigation) already assume by design
convention (docs/modules/dup.md's Rust core section: "the crate is
compute-only ... all IO, caching policy, and git awareness stay in
Python").

Investigate whether a genuinely compute-only kernel boundary can be cut
out of either gate's analysis (e.g. a bounded sub-computation that
already operates on plain data once frob.lang has done the tree-sitter
work) rather than assuming the whole gate needs porting, or conclude
honestly that porting either would require re-implementing a
parser-equivalence/AST-walking layer in Rust that this audit did not
size and is out of scope for a "rust-candidate row migration" ticket.
T-0930's dead_symbols finding (frob_core kernels measured net SLOWER
than pure-Python at this repo's real per-package/per-symbol data scale
due to PyO3 marshaling overhead) is directly relevant context: any
proposed kernel boundary here should be sized against real data volumes
BEFORE porting, not assumed to win from algorithmic argument alone.
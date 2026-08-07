---
id: T-0953
title: port archgate's near-duplicate body-similarity clustering to frob_core (measured
  rust-candidate sub-boundary)
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: T-0951
tier: ticket
sprint: null
scope:
- src/frob/arch/_python.py
- frob-core/src/lib.rs
- tests/test_arch*.py
- frob-core/frob_core.pyi
- docs/audits/check-performance.md
- docs/modules/dup.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_arch_near_duplicate_native.py::test_native_kernel_matches_difflib_on_synthetic_archgate_fixture
- tests/test_arch_near_duplicate_native.py::test_native_kernel_matches_difflib_over_this_repos_own_arch_tree
- tests/test_arch_near_duplicate_native.py::test_near_duplicate_cluster_dispatches_to_native_and_matches_reference
designated_repro_test: null
threat: null
component: null
---
Found while working T-0951 (archgate/pii_structural rust-candidate
feasibility). archgate's `_check_abstraction_opportunities` detector
(`src/frob/arch/_python.py::_near_duplicate_cluster`) does pairwise
`difflib.SequenceMatcher(None, a, b).ratio()` similarity scoring over
already-normalized body-fingerprint STRINGS (plain data, not
tree-sitter Node objects) within same-signature function groups.
Measured (non-profiled, this repo's own tree): ~3.1s of archgate's
11.57s baseline wall time (~27%), isolated by monkeypatching the
function to a no-op and diffing wall-clock. A cProfile pass separately
attributed 107,024 difflib.find_longest_match calls as the single
largest leaf.

This matches frob_core's existing compute-only precedent
(`tree_edit_similarity`/`apted_similarity` in frob.dup._core --
statement-hash-sequence similarity, plain data in/out) closely enough
to be a genuine rust-candidate, unlike the rest of archgate (dominated
by tree-sitter Node-shaped SOLID/LSP detectors) or pii_structural
(dominated by ast/Node walks feeding cheap dict-lookup matching) --
both of those were disposed as NOT rust-candidates in T-0951's
decision (docs/audits/check-performance.md's "Remediation log
(T-0951)" section).

Implement: a frob_core kernel taking one same-signature group's
`list[str]` (body_fingerprint texts) and returning the near-duplicate
index set (mirroring `_near_duplicate_cluster`'s existing contract),
batched ONCE PER GROUP (not once per pairwise comparison -- this is
the batching shape T-0930's reverted resolve_call_edges prototype did
NOT have, and its lack is exactly why that prototype measured net
slower). Required before wiring as the default path, per T-0930's own
precedent:
- golden parity test: native result byte-identical to
  difflib.SequenceMatcher.ratio() at the existing
  _BODY_SIMILARITY_THRESHOLD = 0.9 cutoff, over both a real
  archgate-triggering fixture and this repo's own src/frob/arch tree.
- a real marshal-vs-compute cost measurement with the kernel actually
  built (median of several runs, thread_time, same methodology as
  T-0930's benchmark) -- do NOT ship as the default path if measured
  net slower than the existing pure-Python difflib path, matching
  T-0930's own disposition when its prototyped kernels lost to
  marshaling overhead.
- byte-identical pure-Python fallback when frob_core is unavailable
  (the worktree-natives-artifact pattern T-0930 also used).
---
id: T-0800
title: 'dup: normalize combined-vs-split early-return conditionals before similarity
  compare'
state: dropped
kind: feature
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/**
- frob-core/src/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_dup.py::TestRealGitCommonDirPairRegisters::test_real_git_common_dir_pair_registers_as_a_duplicate_group
designated_repro_test: null
threat: null
component: null
---
Found while working T-0785 (dup: normalize error-channel before similarity
compare). The ticket's motivating case -- frob.tickets._leases.git_common_dir
(Result[Path, LeaseError]) vs frob.gates._exclude_hazard._git_common_dir
(Path | None) -- differs along TWO independent axes, not one:

1. Error-channel shape (Err(...)/Ok(...) vs None/bare value) -- T-0785
   normalizes this axis. Fixed.
2. Combined-vs-split early-return conditional: git_common_dir merges both
   failure checks into one `if spawned.is_err or spawned.danger_ok
   .returncode != 0:` (both branches map to the SAME Err(LeaseError
   .GitCommonDirUnavailable)), while _git_common_dir keeps them as two
   separate `if`s because each logs a DIFFERENT debug message. This axis
   is NOT normalized by T-0785.

With only axis 1 normalized, the real current pair's R4 near-miss floor
similarity measures 0.444 (frob.dup._pipeline._R4_SIMILARITY_FLOOR =
0.6) -- it does not register as a duplicate group today. A fixture with
axis 2 also aligned (both sides using the same combined-if structure)
reaches 0.799 and registers cleanly (rung r4).

Scope sketch: a control-flow-level token normalization (or a real
AST-level desugar, similar in spirit to R3's elif-desugar in
frob_core::r3_canonicalize) that recognizes "N early-return branches each
guarding a distinct condition, all exiting with an error-channel exit"
as equivalent to "one early-return branch guarding the disjunction of
those conditions" when the exit shapes are otherwise interchangeable.
Needs real AST structure (branch condition/body pairs), not a flat
token-stream heuristic like T-0785's error-channel marker -- likely a
frob_core kernel addition (parallel to r3_canonicalize's elif desugar)
rather than a pure-Python _pipeline.py transform.

## Drop reason
- 2026-07-23: superseded by T-0801 (landed 1a40a97b): guard-shape normalization implemented purely in dup/_pipeline.py covers combined-vs-split early-return conditionals; no Rust-kernel work needed
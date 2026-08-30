---
id: T-3477
title: 'PERF005/PERF008/PERF014: burn down remaining findings after T-2376''s partial
  pass'
state: done
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob-core/src/capability_python.rs
- strata-core/src/graph/model.rs
- src/frob/gates/_rule_id_scan.py
- src/frob/vet/_capability_scan.py
- tickets/T-3479/**
- tests/gates/test_rule_id_scan_branches.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets/T-3479/**
  reason: T-3477's own out-of-scope discovery filed as a new ticket via frob ticket
    new from this worktree; the ticket file itself lands with this ticket
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/gates/test_rule_id_scan_branches.py
  reason: T-3477's PERF014 rewrite of scan_candidate_rule_id_literals needs a multi-line-file
    test that actually exercises the new per-file offset-to-lineno arithmetic (bisect
    over cumulative per-line byte offsets), which the existing single-line fixtures
    never touch and TEST016's mutation check caught as a live gap
  actor: logan
  at: '2026-08-30'
body_changes:
- mode: append
  reason: 'BUG002 land-time gate: T-3477 is a behavior-preserving perf rewrite (algorithmic,
    not a functional defect fix), needs frob:no-behavior-change to land'
  actor: logan
  at: '2026-08-30'
  old_length: 1775
  new_length: 2544
evidence:
- tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_finds_bare_positional_argument
- tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_finds_code_kwarg_outside_scanned_bases
- tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_finds_typed_const_assignment
- tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_inline_comment_example_not_picked_up
- tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_whole_line_comment_not_picked_up
- tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds::test_detects_freshly_added_rule_id
- tests/test_vet.py::TestOpaqueIndirectionGate::test_kotlin_operator_invoke_instance_call_fires
- tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_reports_correct_line_number_deep_into_a_multi_line_file
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2376 fixed the 9 Python-file PERF005 unproven-recursion findings via
frob:invariant terminates directives (src/frob/gates/_dead_symbols.py,
src/frob/gates/_walk_lint.py, src/frob/graph/summary.py,
src/frob/vet/_supplychain.py). Measured remaining via
frob check --only perf --json 2026-08-30:

PERF005 (6): frob-core/src/capability_python.rs (5 sites:
collect_target_names:241, resolve_expr:344/380/404, collect_candidates:760),
strata-core/src/graph/model.rs::new:257 -- Rust files, same fix shape (a
termination justification) but needs the Rust-side directive-comment
mechanics confirmed (frob:invariant syntax in // comments) before applying.

PERF008 (83): calls-in-a-loop-with-loop-invariant-arguments across ~35 files
(hooks, scripts, src/frob, tests) -- NOT mechanically fixable in bulk;
several sampled findings (e.g. scripts/fleet_status.py's per-entry
fd.resolve()/iterdir() inside a per-process loop) look like they may be
false positives (the loop variable IS the effective argument, not
invariant) rather than genuine hoist-out-of-loop opportunities -- needs a
per-finding read before fixing or waiving, not a blanket sweep.

PERF014 (2): src/frob/gates/_rule_id_scan.py:389,
src/frob/vet/_capability_scan.py:1228 -- both are single-pattern-per-line
loops the detector flags as pattern-list-shaped; a real fix means
restructuring to one whole-text finditer() call per pattern with line
numbers computed from string offsets, preserving today's per-line
comment-stripping behavior -- a real algorithmic rewrite, not a one-line
change, and risky to get right without dedicated attention.

Severity was NOT promoted to error in frob.toml -- the family is not at
zero. Promote only once every code above is at zero, per T-2376's/the
epic's own acceptance criteria.

frob:no-behavior-change reason="T-3477 is a PERF burn-down: 5 frob:invariant terminates \
directive comments added to already-correct, already-recursive Rust functions (no \
functional change, comment-only), plus two PERF014 algorithmic rewrites \
(scan_candidate_rule_id_literals/_kotlin_operator_invoke_call_lines) that are \
deliberately, explicitly behavior-preserving refactors -- same finditer() matches, same \
line numbers, same first-occurrence/per-construction multiplicities, verified equal via \
the existing test suite plus a new multi-line-file regression test. There is no defect \
this ticket's diff fixes in caller-visible behavior; BUG002 asking for a test that fails \
at main and passes at the fix does not apply to a same-behavior perf rewrite."
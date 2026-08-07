## Done report

Measured 61 COV006 findings via `frob check --only coverage` on this
worktree before starting (2 within gates/__init__.py+test_gates.py,
already resolved by T-0516; 59 outside that scope, per this ticket's
mandate). Triaged all 59:

- 3 were genuinely wrong/self-referential bindings, fixed directly:
  * tests/unit/test_check.py::TestSummarySeverityHonesty
    .test_cycle_summary_splits_by_severity rebound from _run_cycle (never
    called by this test) to _severity_counts_summary (what it actually
    imports and calls).
  * tests/system/test_cli_check.py's _make_polyglot_project fixture
    helper carried a frob:tests directive naming ITSELF as its own
    tested target -- removed (nonsensical self-edge).
  * src/frob/strata/_waive.py's _stale_detail carried the same
    self-referential shape, duplicating real passing coverage already at
    tests/unit/strata/test_waive.py::TestStaleDetail
    .test_names_rule_node_and_reason -- removed the redundant directive.

- The remaining 56 all fall into four systematic checker-blindness classes
  that neither T-0516's two-hop same-file rescue nor _cov006's 2-file
  scoped build_call_graph can see:
  1. Framework/language-implicit dispatch (14): pydantic
     @field_validator methods, module __getattr__, context-manager
     __exit__ -- invoked by the runtime/decorator machinery, never a
     literal name(...) call the token scanner can see.
  2. 3+-file call chains (33): the test calls a public entrypoint in a
     THIRD file (neither test's own file nor the target's file), which
     calls a public wrapper in the target's own file, which reaches the
     private target -- _cov006_public_wrapper_reachable's rescue only
     checks whether the test's OWN literally-called name is itself a
     public symbol in the target's file, so it can't see this shape.
  3. CLI/subprocess integration boundary (2): argparse subcommand
     dispatch / subprocess invocation, no literal call visible at all.
  4. No Rust call-graph support (7): frob-core/src/lib.rs's #[cfg(test)]
     inline tests calling their own module's private fns -- Rust isn't
     resolved by build_call_graph the way Python same-file calls are.

  Not Filed T-draft-bfda63d4 (never refiled) (renumbers on merge to main) as ONE calibration
  ticket covering all four classes with the exact finding list (test node
  id -> target symref) and per-class fix direction, per the "skip its
  findings, listing them" policy -- rather than hand-waiving 56 individual
  findings (which T-0525's separate file-scope-waiver-granularity bug
  would make unsafe: one COV006 waiver in a file silently suppresses ALL
  COV006 findings in that file, including any future genuine one).

Verified post-fix: `frob check --only coverage` COV006 count dropped from
61 total (59 outside gates/__init__.py+test_gates.py) to 58 total (56
outside that scope), confirmed by direct grep-count on the fresh check
output -- exactly 59 - 3 fixed = 56.

### Changed
```
 src/frob/gates/__init__.py     |  20 ++-
 src/frob/strata/_waive.py      |   6 +-
 src/frob/tickets/_models.py    |  25 +++-
 tests/system/test_cli_check.py |   7 +-
 tests/test_gates.py            |  19 +++
 tests/test_tickets.py          |   9 ++
 tests/unit/test_check.py       |   5 +-
 tickets.md                     | 287 +++++++++++++++++++++++++++++++++++++++--
 8 files changed, 363 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/unit/test_check.py::TestSummarySeverityHonesty::test_cycle_summary_splits_by_severity` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_waive.py::TestStaleDetail::test_names_rule_node_and_reason` (pytest node id, verified passing when recorded)

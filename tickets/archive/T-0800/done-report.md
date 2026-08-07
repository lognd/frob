## Done report

Resolved by sibling ticket T-0801, not separately.

T-0800 and T-0801 describe the exact same finding: the real
frob.tickets._leases._git_common_dir / frob.gates._exclude_hazard
._git_common_dir pair differs on a combined-vs-split early-return
conditional axis, independent of T-0785's error-channel axis. T-0800's
Plan/Scope-sketch speculated a frob_core (Rust) kernel addition might be
needed for this ("likely a frob_core kernel addition ... rather than a
pure-Python _pipeline.py transform") -- that speculation predated actually
attempting the fix. The full normalization (condition abstraction,
guard-exit-body collapse, adjacent-duplicate-guard folding) turned out to
be implementable entirely as pure-Python token-stream transforms in
src/frob/dup/_pipeline.py, with no frob-core/Rust changes needed, so I
implemented it under T-0801 (the narrower, better-fitting, python-only-
scoped sibling) rather than splitting the same work across two tickets.

See T-0801's Done report for the full implementation description,
measured test/gate numbers, and the two real bugs hit and fixed along the
way (guard-span boundary, elif condition abstraction). No frob-core/src/**
change was made or needed -- T-0800's scope allowance for frob-core/src/**
went unused.

No changes made under T-0800 specifically; no out-of-scope discoveries;
no drafts filed. Deferring close-vs-drop of this ticket to the
coordinator, per dispatch instructions -- recommend `drop` (superseded by
T-0801) since T-0801 fully covers the finding, but the decision is the
coordinator's.

### Changed
```
 src/frob/dup/_pipeline.py | 239 +++++++++++++++++++++++++++++++++++++-
 tests/test_dup.py         | 284 ++++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                | 101 ++++++++++++++++-
 3 files changed, 617 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_dup.py::TestRealGitCommonDirPairRegisters::test_real_git_common_dir_pair_registers_as_a_duplicate_group` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

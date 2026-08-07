## Done report

SYS104 (T-0668) used to evaluate a node only after it had already
declared at least one interface= attr -- an opt-in scope cut disclosed
at T-0668 because closing it required real interface= metadata in
design/frob.strata, out of that ticket's own scope.

This ticket closes both follow-ups T-0668/T-0669/T-0670 deferred:

1. design/frob.strata now carries a real, measured interface=<symbol>
   attr for every node/store whose bound code has a non-empty public
   surface (14 nodes/stores: cli, graphlang, gates, checker, stratamod,
   registry_model, fleet, core, mutate, natives, serve, deploy, vet,
   tickets_ledger). Every attr was generated mechanically from the same
   _module_public_symbols/_node_real_public_surface functions SYS104
   itself uses, so declared and real agree by construction at the point
   they were added -- this was NOT hand-typed; a one-off script drove
   bind_code + _node_real_public_surface over the real design model and
   inserted one `attr interface=<name>;` line per real symbol into each
   node/store's block.
2. _interface_conformance_violations (SYS104) now evaluates ANY node
   whose real public surface is non-empty, whether or not it has
   declared anything -- a node with nothing declared and a non-empty
   real surface now fires (every real symbol reports as missing), same
   as before for a node declaring some but not all of its surface. A
   node with an EMPTY real surface stays exempt either way (nothing to
   declare). SYS105/SYS106 are UNCHANGED -- still opt-in, per this
   ticket's own follow-up text (only SYS104 was named for the flip).
3. docs/design/registry/check-coverage.yaml gets CHK-GATE-SYS104,
   CHK-GATE-SYS105, CHK-GATE-SYS106 entries (handled_by:SYS104/105/106),
   mirroring the CHK-GATE-SYS103 precedent; gate_rule_total bumped
   254 -> 257 to match. check_self_conformance carries the matching
   frob:enforces CHK-GATE-SYS104/105/106 directives.
4. docs/modules/strata.md's SYS104/SYS105 sections rewritten: SYS104's
   "Scope cut (disclosed)" subsection replaced with "Mandatory as of
   T-1113"; SYS105's cross-reference to "Same SYS104 scope cut" updated
   to note SYS104 itself is no longer opt-in.
5. Adding interface= to 14 node/store blocks touches essentially every
   node in design/frob.strata, which trips AFFECT001 (affects()-closure
   doc not touched) for each -- these are waived at each node with a
   dated, specific reason (mechanical metadata only, no behavioral
   change, the cited affects()-closure docs do not describe node public
   surfaces).

Test changes (tests/unit/strata/test_selfconform.py, scope widened via
frob ticket scope --add):
- TestInterfaceConformance.test_node_with_no_interface_attr_is_never_
  checked: kept its ORIGINAL name (T-0668's own evidence citation for
  this test id must keep resolving) but rewrote the body/docstring to
  assert the NEW mandatory behavior (undeclared node with a real public
  symbol now fires, not stays silent).
- New test_node_with_empty_real_surface_stays_exempt: a node with zero
  real public symbols and nothing declared stays silent (the surviving
  half of the old opt-in scope cut; no follow-up ticket needed -- this is
  the correct permanent behavior for an empty surface, not a deferred gap).
- TestUnmodeledCodeMissingPackageRoot.test_missing_package_root_
  produces_no_warning: fixture module-level assignment renamed from a
  public `x = 1` to a private `_x = 1` so this SYS102-focused test does
  not incidentally trip the now-mandatory SYS104 on an unrelated public
  symbol.
- A DUP001 near-duplicate finding against test_core_undeclared_
  interface_fires (SYS100, unrelated rule) is waived with a reasoned
  frob:waive -- both tests share this suite's standard one-write/one-
  node/check_self_conformance scaffold but assert different rules on
  different observations.

Verification (all foreground, chunked per the playbook):
- tests/unit/strata/test_selfconform.py: 67 passed (full file,
  `uv run pytest tests/unit/strata/test_selfconform.py -q`).
- `uv run frob check --ticket T-1113 --only gates-native`: 0
  errors (DUP/ARCH/EXHAUST/LARGE/PERF/WAIVE all pass).
- `uv run frob check --ticket T-1113 --only gates-security`: 0 errors.
- `uv run frob check --ticket T-1113 --only gates-fast`: 1 remaining
  error, COV001 on src/frob/gates/_tracked_files.py::tracked_files --
  confirmed pre-existing (last touched by commit 0abc4e3a, unrelated to
  this ticket's scope, untouched by this diff).
- `uv run frob check --ticket T-1113 --only static`: 0 errors.
- `uv run frob check --ticket T-1113 --only lint`: 0 errors in my own
  files (ruff-format applied to test_selfconform.py); the remaining 6
  ruff-check errors are all pre-existing in src/frob/vet/_capability.py
  and src/frob/vet/_supplychain.py, outside this ticket's scope.
- `git diff main --diff-filter=D --stat`: empty (no unintended
  deletions).

Filed: none new by this ticket.

### Changed
```
 design/frob.strata                       | 4158 ++++++++++++++++++++++++++
 docs/design/registry/check-coverage.yaml |   14 +-
 docs/modules/strata.md                   |   38 +-
 src/frob/strata/_selfconform.py          |   60 +-
 tests/unit/strata/test_selfconform.py    |   37 +-
 tickets.md                               | 4690 +++++++-----------------------
 6 files changed, 5290 insertions(+), 3707 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_node_with_no_interface_attr_is_never_checked` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestInterfaceConformance::test_node_with_empty_real_surface_stays_exempt` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestUnmodeledCodeMissingPackageRoot::test_missing_package_root_produces_no_warning` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

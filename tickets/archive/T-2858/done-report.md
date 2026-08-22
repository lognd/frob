## Done report

Re-measured T-2858's 4 declared findings on current main (already includes
T-2801's landed fix, f60eb5404c7480775e98401b1aaf54ad074ef219, verified as
an ancestor of this worktree's HEAD via `git merge-base --is-ancestor`)
via `frob check --only gates-fast --ticket T-2858 --json`, unbudgeted,
gate-summary present:

- DRIFT002 x4 docs/modules/tickets-data-storage.md -- GONE. T-2801 already
  repointed all 4 `frob:describes` edges
  (migrate_to_ledger/migrate_v1_to_v2/_migrate_one_v2/_split_done_report)
  from `_store.py` to `_store_migrate.py`, confirming this ticket's
  suspected root cause (T-2695's migration-function split) directly.
- DOC006 docs/audits/test005-zero-classification-t1418.md -- GONE. T-2801
  already repointed the stale `#6d-test005-reads-coveragexml-and-
  make-coverage-deletes-it` anchor to the current
  `#6d-test005-reads-coveragexml-and-the-full-suite-coverage-refresh-
  deletes-it` heading.
- COV001 src/frob/graph/callgraph.py::build_call_graph -- GONE. T-2801
  already added the `frob:doc` edge to docs/audits/graph.md's existing
  accurate description.
- TEST001 src/frob/strata/_multifile.py::SealedGrantSet.from_root_node --
  GONE. T-2801 already added `frob:tests` edges to the 3 pre-existing
  real tests in tests/unit/strata/test_fragments.py.

No code changes made in this ticket's own worktree -- this is a
duplicate-of-fixed closure, not a new fix. Root cause (T-2695's
`_store.py` migration-function split, as this ticket's own body
suspected) is CONFIRMED, not just consistent-with: the functions'
current real locations were verified directly in `_store_migrate.py`.

Changed: none (verification-only; the fix already landed under T-2801).

Evidence: re-measurement of `frob check --only gates-fast --ticket
T-2858 --json` shows zero occurrences of any of the 4 declared
(rule, file) identities. No pytest evidence to bind -- this ticket closes
on a gate re-measurement showing its own findings gone, not a code change
of its own.

Filed: none.

Gates: all 4 of this ticket's own declared findings are absent from a
fresh, unbudgeted, gate-summary-present check run. Closing as resolved by
T-2801 (f60eb5404c7480775e98401b1aaf54ad074ef219), not landing a separate
commit.

### Changed
```
 tickets/T-2858/ticket.md | 22 ++++++++++++++++++++--
 1 file changed, 20 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_widen_on_declared_atom_still_works` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_widen_on_undeclared_atom_refuses_closed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_fresh_insert_raises_at_runtime` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 27 error(s), 652 warning(s), 798 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@design/frob.strata, COV003@tickets/T-1102, COV003@tickets/T-1651, COV003@tickets/T-1656, COV003@tickets/T-2375, COV003@tickets/T-2822, COV003@tickets/T-2823, COV003@tickets/T-2824, COV003@tickets/T-2825, COV003@tickets/T-2826, COV003@tickets/T-2829, COV003@tickets/T-2830, COV003@tickets/T-2839, CYCLE001@src/frob/__init__.py, DOC006@docs/modules/graph.md, DOC006@tickets/T-2860/ticket.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DOCENUM001@docs/modules/gates.md, DRIFT002@docs/modules/tickets-landing.md, OPAQUE001@src/frob/gates/_refs.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md

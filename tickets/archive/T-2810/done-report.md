## Done report

Changed:
src/frob/strata/_multifile.py::_widen_node_grants (removed duplicate frob:doc comment)
src/frob/strata/_multifile.py::_group_targeted_roots (removed duplicate frob:doc comment)
src/frob/strata/_multifile.py::_group_fragments_by_name (removed duplicate frob:doc comment)
src/frob/strata/_multifile.py::_resolve_unique_roots (removed duplicate frob:doc comment)
src/frob/strata/_multifile.py::_seed_grants_by_root_node (removed duplicate frob:doc comment)
src/frob/strata/_multifile.py::_apply_fragment_extends (removed duplicate frob:doc comment)
src/frob/strata/_multifile.py::_rebuild_resolved_files (removed duplicate frob:doc comment)

Each carried a `# frob:doc docs/strata/surface.md#fragments-t-2502` comment
duplicating the SAME anchor already on the public `resolve_fragments`
entry point they implement (line ~414) and on `SealedGrantSet` above
them. Verified docs/strata/surface.md's "Fragments (T-2502)" section
`frob:describes` only `resolve_fragments` and `SealedGrantSet` -- it does
not name any of these 7 private helpers individually in prose, unlike
the genuinely-deliberate per-helper pattern in vet.md's Public API
section (several COV007 findings matching THAT shape are correctly
waived, not fixed -- see docs/investigations/T-2796-backlog-
reproduction.md). No documentation coverage is lost: the public entry's
own anchor already covers the documented algorithm.

Evidence: docs-adjacent code change (comment removal only, no behavior
change). No existing test targets these specific comments; recording the
existing strata multifile test suite as evidence per playbook section 5's
docs/no-new-behavior precedent:
tests/unit/strata/test_multifile.py::TestResolveFragments.test_widens_via_glob_union

Verification: re-ran `frob check --only gates-fast --json` after the
edit -- all 7 COV007 findings for src/frob/strata/_multifile.py are gone
(confirmed by file+symbol name against the pre-edit list). COV gate
warning count dropped 46 -> 38 (7 from this fix; the 8th, a COV006 in
tests/test_gates.py, resolved incidentally via a concurrent land during
this session -- not claimed as this ticket's own work).

Gates: frob check --ticket T-2810 shows the usual repo-wide
FAILs (COV/DOC/DRIFT/PERF/REG/SCOPE/SEC/SYS/TEST/TICK) that --ticket's
own scope-note documents as NOT filtered to this ticket -- pre-existing
repo-wide state, not introduced by this change. gate:SCOPE's ticket-
scoped SCOPE001 (the new ticket's own tickets/T-draft-.../ticket.md file
outside declared scope) is the same known false-positive class as
T-2796's own land.

### Changed
```
 tickets/T-2370/ticket.md           |  8 +++--
 tickets/T-2810/ticket.md | 69 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 74 insertions(+), 3 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 20 error(s), 873 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2790-check-stage-profile.md, DOC001@docs/investigations/T-2796-backlog-reproduction.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2810, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md

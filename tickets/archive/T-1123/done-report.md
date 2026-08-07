## Done report

Extracted ONE cohesive family from src/frob/tickets/__init__.py (T-1108/
T-1103 residue), following the same extraction pattern precisely:
smallest cohesive unit, private module, public surface re-exported via
`from frob.tickets._scope import mutate_scope` + existing `__all__`
entry, zero caller-visible behavior change, frob:tests/frob:doc
directives moved verbatim with the functions they annotate.

Moved to new src/frob/tickets/_scope.py (395 lines): mutate_scope (the
public `frob ticket scope --add/--remove` entry point) and every private
helper it alone leans on -- _current_actor, _scope_add_conflicts,
_is_new_concrete_file_glob (T-0561's new-file carve-out),
_scope_remove_orphans_evidence, _validate_scope_request,
_validate_scope_mutation, _warn_over_broad_adds, _scope_change_entries,
_write_scope_mutation.

_load_ticket_and_queue (the merged active+archive load+lookup
mutate_scope needs) deliberately STAYS in __init__.py -- it is also
set_priority/set_kind/set_tier/set_sprint's own shared load helper, not
scope-specific -- so mutate_scope late-imports it from the package at
call time (`from frob.tickets import _load_ticket_and_queue`), the same
load-order-safe indirection T-1103/T-1108 already established for
renumber_one/doable's own forward references (documented directly in
mutate_scope's own docstring so a future reader does not "fix" it back
to a module-top-level import and reintroduce the circular-import
failure).

tickets/__init__.py: 3070 -> 2740 lines (330 carved) -- progress toward
the acceptance criterion's <2000 target, still above it. _land.py (4762
lines) was not touched at all in this pass.

Verified zero monkeypatch breakage: grepped for any test/source
reference to the moved private helpers via the tickets_mod.<name>
package-attribute pattern T-1103's Done report warned about -- none
exist for this family (only mutate_scope itself is referenced anywhere
outside _scope.py, always via `from frob.tickets import mutate_scope`,
which the re-export keeps working unchanged).

Updated docs/modules/tickets.md: the mutate_scope frob:describes anchor
now points at _scope.py, plus a short note in the "Scope/lease change
protocol" section naming the new module and the extraction precedent.

REQUEUING WITH RESIDUE: per the coordinator's own instruction ("do as
many families as budget allows; requeue-with-residue honestly at the
end"), only the scope-mutation family was extracted this pass. Filed a
follow-up draft ticket for the three remaining families T-1123's own
body names (field setters/sprint, evidence/transition -- BEWARE the
load-time circular import T-1103's Done report flagged for that exact
family -- and done-report/review/drop/attach) plus _land.py's own split
(4762 lines, not touched at all).

Filed: T-1151 (arch: extract remaining families + split
_land.py -- renumbers at land; cite the real id once landed).

### Changed
```
 docs/modules/tickets.md      |  10 +-
 src/frob/tickets/__init__.py | 332 +-----------------------------------
 src/frob/tickets/_scope.py   | 395 +++++++++++++++++++++++++++++++++++++++++++
 tickets.md                   |  63 ++++++-
 4 files changed, 465 insertions(+), 335 deletions(-)
```

### Evidence
- `tests/test_tickets_scope_mutation.py::TestMutateScope::test_add_free_path_granted` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestMutateScope::test_add_leased_path_rejected_names_holder` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestMutateScope::test_remove_frees_path_for_other_doable` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestNewFileCarveOut::test_new_file_under_broad_lease_is_exempt` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestNewFileCarveOut::test_existing_file_under_broad_lease_still_conflicts` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestNewFileCarveOut::test_new_file_exact_match_of_holder_scope_still_conflicts` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 25 error(s), 973 warning(s), 431 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, ARCH001@src/frob/doctor.py, ARCH001@src/frob/tickets/__init__.py, COV001@src/frob/gates/_tracked_files.py, COV003@tickets/T-0138, COV003@tickets/T-0226, COV003@tickets/T-0629, COV003@tickets/T-0700, COV003@tickets/T-0702, DUP001@src/frob/tickets/_scope.py, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/vet/_supplychain.py:295, F401@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/tickets/__init__.py:111, F401@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/tickets/__init__.py:22, F401@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/tickets/__init__.py:23, F401@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/tickets/__init__.py:35, F401@/home/logan/projects/frob/.claude/worktrees/w18-tickets/src/frob/tickets/__init__.py:46, INV006@src/frob/app/stats_runner.py, PII012@tests/system/test_cli_doctor.py, SELFAUDIT001@design

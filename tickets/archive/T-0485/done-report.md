## Done report

Root cause: `_scope_add_conflicts` checked an `--add` glob against every OTHER
in-progress ticket's declared scope with no exemption for globs the
requesting ticket ALREADY covers. A queued ticket that grandfathers a broad
glob (e.g. `src/frob/strata/**`) overlapping an in-progress ticket's lease
could never narrow that overlap down to a concrete subset path (e.g.
`src/frob/strata/_host.py`) -- the narrowing itself was rejected as a fresh
`ScopeLeaseConflict`, even though it strictly SHRINKS contention and can
never create new contention.

Fix: added `_glob_is_subset(narrow, broad)` (src/frob/tickets/_models.py) --
exact when `narrow` is a concrete literal path (delegates to
`fnmatch.fnmatch`), conservatively `False` whenever `narrow` still carries a
wildcard (so a genuine expansion can never slip through disguised as a
narrowing). `_scope_add_conflicts` now takes the requesting ticket's own
pre-mutation `scope` and exempts any `--add` glob that is a subset of
something already in it, before ever checking against other holders'
leases. `_validate_scope_mutation` passes `ticket.scope` through.

Re-narrowing the 16 tickets listed in T-0485's body: read all 16 ticket
bodies (T-0235, T-0261, T-0339, T-0341, T-0383, T-0384, T-0392, T-0393,
T-0394, T-0395, T-0401, T-0410, T-0428, T-0440, T-0160, T-0461). Disclosing
plainly: none of them yielded a genuinely narrower concrete touch set
distinct from what they already declare -- they are open-ended audits/
reconciliations/refactor sweeps (arch-advisory triage across src/frob/,
registry-vs-enforcement reconciliation across the whole capability matrix,
a repo-wide perf audit, a coverage backlog spanning ~78 modules) whose
declared breadth is what the described work actually requires, not an
artifact of the T-0455-era sweep failing to narrow them. Fabricating a
concrete file list not actually derived from the body would misrepresent
scope for whoever picks these up next, so no scope mutation was applied to
any of the 16. Also, only T-0401 is currently in-progress among them
(holding `src/frob/strata/`) -- the other 15 are queued and not blocking
any live lease today; `frob ticket doable | grep WARNING` count is
unrelated to lease contention (breadth-threshold nudges, not lease
rejections) and was not the mechanism this bug affected. The concrete,
verified fix is the mechanism itself (proven by the two new
TestMutateScope cases below), available for any agent to invoke on any of
the 16 once it identifies a real narrower touch set from its own work.

REL001: not required -- no public symbol's signature/behavior changed
(`_scope_add_conflicts`/`_validate_scope_mutation` are private; the new
`_glob_is_subset` is private). `frob release check` reports OK at 0.53.0
unchanged.

### Changed
```
 src/frob/tickets/__init__.py         | 21 +++++++++--
 src/frob/tickets/_models.py          | 17 +++++++++
 tests/test_tickets_scope_mutation.py | 58 ++++++++++++++++++++++++++++-
 tickets.md                           | 72 ++++++++++++++++++++++++++++++++++--
 4 files changed, 161 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_tickets_scope_mutation.py::TestMutateScope::test_add_subset_of_own_leased_overlap_is_accepted` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestMutateScope::test_add_beyond_own_leased_overlap_still_rejected` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestGlobIsSubset::test_concrete_path_under_double_star_is_subset` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestGlobIsSubset::test_wildcard_bearing_narrow_is_never_subset` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestGlobIsSubset::test_concrete_path_outside_broad_glob_is_not_subset` (pytest node id, verified passing when recorded)

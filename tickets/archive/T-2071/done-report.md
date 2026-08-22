## Done report

Changed:
- src/frob/scaffold/project.py::_WORKTREE_LEASE_HOOK_SCRIPT (added a second, FROB_AGENT-independent guard)
- src/frob/scaffold/project.py::install_worktree_lease_hook (docstring updated to describe the new guard)

Evidence:
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_agent_context_root_write_refused_without_frob_agent (--accepts 1, designated repro: FAILED_AT_PARENT at e5780d953, confirmed with --check-repro)
- tests/test_scaffold_worktree_lease_hook.py full class: 16 passed (was 15; +1 new test, 0 regressions)
- criterion 3 (fleet_status.py names offending paths on a dirty root) already holds on main, unchanged by this ticket: tests/unit/test_coordinator_scripts.py::TestRootDirt::test_dirty_repo, 2 passed -- fleet_status.root_dirt()/main() already return/print per-path porcelain lines, not a bare verdict.

Filed:
- T-2119 (docs): document the new guard in docs/commands/scaffold.md#public-api once T-1382's live lease on docs/commands/** frees (out of T-2071's own scope; AFFECT001 waived with this reason)
- T-2118 (bug): criterion 2's remaining gap -- _log_dirty_main_refusal (src/frob/tickets/_land.py) should name the OWNING ticket when dirt belongs to some OTHER open ticket's scope, not just distinguish "no open ticket" from generic; could not be done under T-2071 because src/frob/tickets/_land.py was held by T-2105's live cross-worktree lease for T-2071's entire duration.

Gates: frob check --ticket T-2071 clean except:
  - gate:SCOPE SCOPE001 on tickets/T-2119/ticket.md -- pre-existing gap: the SCOPE001 cross-ticket exemption's ticket-ref regex (_TICKET_REF_RE = T-\d{4}) does not match a draft id's commit subject, so filing a residue ticket from inside another ticket's worktree always trips this; not caused by this ticket's own diff content, not fixed here (regex touch would be its own out-of-scope change to src/frob/gates/__init__.py).
  - gate:TICK TICK004 (T-0969 rotting, 15d) -- pre-existing repo-wide backlog rot, unrelated to this ticket's files.
  - ruff-format (110 files repo-wide) -- pre-existing, unrelated to touched files (ruff-check on the touched files alone: All checks passed).
  gate:ARCH/gate:AFFECT/gate:PRE, all clean after fixes (ARCH001 line-count and AFFECT001 waiver, both addressed in this ticket's own diff).

### Changed
```
 src/frob/scaffold/project.py               | 86 ++++++++++++++++++++++++------
 tests/test_scaffold_worktree_lease_hook.py | 45 ++++++++++++++++
 tickets/T-2071/ticket.md                   | 25 +++++++--
 tickets/T-2118/ticket.md         | 24 +++++++++
 tickets/T-2119/ticket.md         | 23 ++++++++
 5 files changed, 184 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_agent_context_root_write_refused_without_frob_agent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: TICK004@tickets.md

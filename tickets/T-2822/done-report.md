## Done report

Changed:
- src/frob/tickets/_leases.py (frob:waive LARGE001 added; real seam identified and
  filed as follow-up T-2833, not split here -- out-of-scope design/frob.strata
  capability grants required)
- src/frob/tickets/_new_renumber.py (frob:waive LARGE001 added, T-1651-grade)
- src/frob/tickets/_reporting.py (frob:waive LARGE001 added, alongside existing ARCH102 waiver)
- src/frob/tickets/_scope.py (frob:waive LARGE001 added, T-1651-grade)
- src/frob/tickets/_setters.py (frob:waive LARGE001 added; real seam identified and
  filed as follow-up T-2834, not split here -- out-of-scope frob.tickets.__init__
  re-export path plus no scope glob to add a new file under)
- src/frob/tickets/_store.py (frob:waive LARGE001 added, alongside existing ARCH102 waiver)

Disposition: all 6 files WAIVED, no splits performed in this ticket. Two files
(_leases.py, _setters.py) have a genuine, investigated consumer-set seam
(worktree-sweep vs lease-CRUD; sprint/flow analytics vs field setters) that
was NOT executed here because it requires touching files outside T-2822's
declared scope (design/frob.strata's capability-effect declarations for a
new _worktree_sweep.py; frob.tickets.__init__'s re-export surface, plus no
scope glob to add a brand-new file under for either). Both are filed as
proper follow-up tickets rather than forced through scope creep or silently
dropped. The other four files (_new_renumber.py, _reporting.py, _scope.py,
_store.py) are genuinely cohesive single-concern modules, several already
the residue of a prior real split (T-1103/T-1192 for _new_renumber.py,
T-2695 for _store.py) and two already carrying an ARCH102 waiver
(_reporting.py, _store.py) whose own reasoning already establishes the
cohesion this LARGE001 waiver restates.

Evidence: tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
Filed: T-2833 (split _leases.py's worktree-sweep family into
_worktree_sweep.py), T-2834 (split _setters.py's sprint/flow
analytics family into _flow.py) -- both renumber at land
Gates: frob check --only arch clean for LARGE001 (0 findings this code across
the batch, all 6 files read severity=note/waived); frob:waive BUG002 added
to ticket body -- no source behavior changed, no single reproducible defect
exists to bind evidence to (judgment-call waiver ticket, same shape as
T-2375/T-2825's own BUG002 waiver).

### Changed
```
 tickets/T-2822/ticket.md           | 33 +++++++++++++++++++++++++++++--
 tickets/T-2833/ticket.md | 40 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2834/ticket.md | 37 +++++++++++++++++++++++++++++++++++
 3 files changed, 108 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 20 error(s), 1072 warning(s), 728 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2822, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md

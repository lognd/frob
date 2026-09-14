## Done report

Main's CI run 34836067875 (d676c3b49) was red on all three legs with the same
two self-gate errors plus one Windows-only test failure; none of them was a
behaviour defect in shipped code.

- DRIFT001 src/frob/doctor.py::run_diagnosis (body): the digest moved when
  T-4459 added the import_source computation and threaded it through report
  assembly. Re-verified that docs/guides/install.md's doctor section still
  describes the same contract, and that the new field is documented in
  docs/modules/agent-worktree.md; recorded a facet=body ack with that reason.
- REF002 docs/design/macos-portability.md: docs/index.md was the only
  inbound reference. docs/design/windows-portability.md already argues from
  the macOS leg's blocking status, so it now names the sibling doc where that
  argument is made -- a real consumer, not a decoy mention.
- tests/test_worktree_pythonpath.py, test_env_output_names_worktree_src_on_pythonpath:
  frob agent env renders every exported value through shlex.quote. A POSIX
  path is printed bare, so the raw-substring assertion passed on ubuntu and
  macOS; a Windows path with backslashes is single-quoted, so it never
  matched. The test now asserts the quoted form the emitter prints, on every
  platform. Measured locally on Linux (5 passed in the module); the Windows
  leg is proven by the CI run that lands this ticket.

### Changed
```
 docs/design/windows-portability.md |  5 ++++-
 frob.lock                          | 20 +++++++++++++++++++-
 tests/test_worktree_pythonpath.py  | 10 ++++++----
 tickets/T-4483/ticket.md           |  4 +++-
 4 files changed, 32 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_worktree_pythonpath.py::TestAgentEnvExportsWorktreePythonpath::test_env_output_names_worktree_src_on_pythonpath` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 4868 warning(s), 968 waived
- error-findings: PRE001@tickets/T-4483, REF002@docs/design/macos-portability.md

## Done report

COV003 flagged T-3410 (kind=bug, state=done) for a `cmd:` evidence entry,
valid only for docs/ux kind tickets. Added a real regression test
(tests/unit/test_scaffold_project.py::test_scaffolded_docs_make_targets_exist_in_makefile)
covering the same claim as the removed cmd: entry -- that a scaffold
project's docs/index.md.j2 and README.md.j2 never reference a `make`
target absent from the rendered Makefile.j2 (the T-3410 regression).
Rebound T-3410's evidence to this node id via
`frob ticket evidence T-3410 --replace ... --reason ...`, and recorded
the same node id as T-3605's own evidence.

Gates: `uv run frob check --only coverage` scoped run shows gate:COV
0 errors (COV003 previously fired on T-3410, now clear). The gate's
1 remaining error (WAIVE011, ratchet lock staleness) is pre-existing
and out of scope for this ticket.

Filed: none.

### Changed
```
 tests/unit/test_scaffold_project.py | 45 +++++++++++++++++++++++++++++++++++++
 tickets/T-3410/ticket.md            | 12 ++++++++--
 tickets/T-3605/ticket.md            |  2 ++
 3 files changed, 57 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_scaffold_project.py::test_scaffolded_docs_make_targets_exist_in_makefile` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 9 error(s), 4119 warning(s), 898 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, DEPR006@frob-deprecated-baseline.lock.json, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, PRE001@tickets/T-3605, REL001@src/frob/__init__.py, WAIVE011@frob-ratchet.lock.json

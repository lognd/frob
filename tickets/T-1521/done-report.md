## Done report

Decision: NO. Flow src/dst validation stays out of elaborate() itself.

Investigated whether elaborate() should validate a flow's src/dst against
declared node ids (the shape check_cross_file_references already applies
for the multi-file elaborate_merged path). A first-attempt implementation
copied the same _known_node_ids join into _validate_references. It broke
two existing, test-covered behaviors in tests/unit/strata/test_boundary_phases.py:

- TestPhaseBlockHappyPath::test_boundary_without_phases_still_elaborates
  elaborates `flow f1 : a -> b` with ZERO node declarations in the module
  and asserts success -- bare elaborate() is relied on today to accept a
  flow whose src/dst name no declared node at all.
- TestPhaseBlockFailClosed::test_refuse_respond_label_must_be_in_labels_lattice
  started failing with the wrong error kind (UnknownReference instead of
  UnknownLevel) because the new check fired first.

Reverted the code/test change and confirmed both tests pass clean on the
unmodified tree. This is real, load-bearing permissiveness, not an
oversight elaborate() can safely close without first understanding what
relies on it -- out of scope for a decision ticket to also design blind.

Recorded the decision and its evidence in docs/strata/surface.md's T-1196
section (the section that originally left this as a T-1521 follow-up).

Filed a narrower, separate follow-up (draft T-1834, renumbers at
land) for the one confirmed real gap: `frob sys export`
(sys_runner.py::_load_export_model) calls elaborate() directly, bypassing
check_cross_file_references entirely, so an exported single .strata file
with an unknown flow endpoint silently builds a KernelModel with a
dangling flow instead of failing closed. That is scoped to the export
path, not elaborate()'s own contract.

### Changed
```
 tickets/T-1521/ticket.md           | 45 ++++++++++++++++++++++++++++++++++++--
 tickets/T-1834/ticket.md | 22 +++++++++++++++++++
 2 files changed, 65 insertions(+), 2 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 7 error(s), 681 warning(s), 739 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/tickets/_doable.py, ARCH103@src/frob/app/ticket_runner/_query.py, COV001@src/frob/registry/_staleness.py, COV001@src/frob/tickets/_doable.py, E501@/home/logan/projects/frob/.claude/worktrees/strata-sys/src/frob/registry/_staleness.py, TEST001@src/frob/registry/_staleness.py

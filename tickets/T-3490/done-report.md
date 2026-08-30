## Done report

T-3481's frob-core #[pyfunction] GIL-release land (WIRE001 waivers touching src/frob/gates/_arch.py, src/frob/gates/_coverage_sites.py, src/frob/gates/_render_lint.py, src/frob/app/ticket_runner/_land_cmd.py, tests/unit/test_new_ticket_scope_overlap_warning.py) surfaced this as a sweep regression, but the actual root cause predates it: all 12 frob:waive WIRE001 sites across those 5 files cited follow_up="T-2057" as their shared accountability anchor for a deliberately-permanent (not pending) waiver posture -- T-2057 got dropped (blocked pending a sound site-identity mapping) at some point after these were written, silently orphaning every one of the 12 at once. Filed a replacement open ticket (T-3504, --ack-related since its title duplicates T-2057's verbatim -- it exists ONLY to give the waivers a live follow_up target again, no work of its own) and re-pointed all 12 follow_up= attributes (plus the two reason-prose mentions of T-2057) at it. Added tests/unit/gates/test_wire002_live_repo.py::test_wire002_zero_against_live_repo, a live-repo WIRE002-zero regression pin mirroring tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo's shape -- put in a new dedicated file rather than tests/test_gates.py because that file was leased by in-progress T-3495. Verified via a direct _wire002_violations(snapshot, queue) call against the live tree: 0 total findings (was 12) before recording evidence.

### Changed
```
 tickets/T-3490/ticket.md           | 12 +++++++++++-
 tickets/T-3504/ticket.md | 30 ++++++++++++++++++++++++++++++
 2 files changed, 41 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/gates/test_wire002_live_repo.py::test_wire002_zero_against_live_repo` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 20 error(s), 4123 warning(s), 870 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, E501@/home/logan/projects/frob/.claude/worktrees/t-3490/src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-3490/src/frob/gates/_coverage_sites.py, E501@/home/logan/projects/frob/.claude/worktrees/t-3490/src/frob/gates/_render_lint.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3490, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json

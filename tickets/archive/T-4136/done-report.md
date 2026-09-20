## Done report

Changed:
- tests/unit/test_land_cmd_drain_wiring.py: TestRapidLandDrainWiring.test_real_rapid_land_spawns_both_sweep_and_drain's spawn_deferred_post_land_sweep double

Evidence:
- tests/unit/test_land_cmd_drain_wiring.py::TestRapidLandDrainWiring::test_real_rapid_land_spawns_both_sweep_and_drain

Filed: none

Gates: the double now restates spawn_deferred_post_land_sweep's real signature
(root, ticket_id, final_id, commit_sha, target_branch=None) instead of the
prior agent's *a, **k catch-all, which would have accepted any future
signature drift silently. Rejected fix: *a, **k -- it makes this double
permanently unable to drift-detect, defeating the reason the ticket exists.

### Changed
```
 tickets/T-4136/ticket.md | 2 ++
 1 file changed, 2 insertions(+)
```

### Evidence
- `tests/unit/test_land_cmd_drain_wiring.py::TestRapidLandDrainWiring::test_real_rapid_land_spawns_both_sweep_and_drain` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 4467 warning(s), 934 waived
- error-findings: LARGE001@src/frob/_cli_parsers/_ticket/_closeout.py, PRE001@tickets/T-4136

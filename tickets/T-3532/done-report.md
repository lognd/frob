## Done report

Fixed both frob_self_scan_heavy tests that ran private whole-repo scans outside T-3495's shared artifacts: (1) tests/unit/test_coordinator_scripts.py::test_waiver_still_suppresses_large001 now builds a SCOPED one-file fixture repo (a real copy of scripts/fleet_status.py under a tmp_path tree) instead of build_graph/arch_gate over the whole live repo -- arch_gate has no snapshot param to piggyback on the shared session fixture, so a scoped fixture-repo scan is this ticket's own accepted alternative. (2) tests/test_gates.py::test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses now consumes a new session-scoped tests/conftest.py::frob_self_scan_snapshot fixture (one build_graph over the real repo per xdist worker, shared by every frob_self_scan_heavy consumer needing a raw snapshot for a gate like perf_gate that takes one) instead of its own private _snapshot(repo_root) call, which also pointed at the real .frob/cache.db rather than a throwaway one. Timing: paired local run of both tests took ~87s wall (mostly the one shared build_graph + perf_gate pass); the LARGE001 test alone is sub-second against the scoped one-file tree. Both tests still fail on their respective planted/real unsuppressed-finding shape -- unchanged real arch_gate/perf_gate/_apply_waivers machinery, only the graph-build cost was routed. Evidence: 3x local pass via FROB_SUGGEST_ACK=1 uv run pytest -p no:xdist on both node ids together. frob check --ticket T-3532 exceeded 300s (exit 143); relied on the scoped runs. Filed: none.

### Changed
```
 tickets/T-3532/ticket.md | 5 ++++-
 1 file changed, 4 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestFleetStatusLarge001WaiverParses::test_waiver_still_suppresses_large001` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestOptInGates::test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 27 error(s), 4131 warning(s), 895 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_process_lock.py, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_process_lock.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3532, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, SELFAUDIT001@docs/design/registry/capability-via-ratchet.lock.json, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json, invalid-argument-type@tests/test_gates.py

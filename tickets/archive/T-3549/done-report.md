## Done report

Round 2 Windows CI diagnosis + attempted fix. Re-measured after T-3540's console-sharing fix landed (run 33361224273): windows-latest STILL DID-NOT-COMPLETE, same KeyboardInterrupt at threading.py:359, same ~1% point -- no ::error::...exceeded message, so Wait-Process never timed out, proving the interrupt is raised INSIDE the pytest process, not delivered externally (rules console-sharing out as the dominant cause). Root cause found by reading the installed execnet package directly: Gateway._terminate_execution (execnet/gateway_base.py:1234-1249) calls _thread.interrupt_main() on win32 when a worker gateway's channel closes uncleanly and its execution pool has not drained within 5s -- exactly this KeyboardInterrupt-on-threading.py shape, internal to execnet/pytest-xdist's own transport teardown, not this repo's code. Ruled out the T-3506 portable lock's Windows branch (_msvcrt_acquire_blocking, src/frob/process/_lock.py): read directly, an unbounded polling loop with no timeout and nothing that could raise KeyboardInterrupt -- a genuine deadlock there would HANG past the 1500s budget (a different, distinguishable failure shape), not interrupt at under a minute. Fix implemented: -p no:xdist added to the windows-latest Test step's pytest invocation, removing xdist/execnet from that leg entirely (ubuntu-latest/macos-latest keep -n auto --dist=loadgroup unchanged, since this mechanism has not misfired there). Cannot verify the fix's real-world effect without a real Windows CI run (no local Windows box) -- explicitly disclosed as unverified pending the next windows-latest run.

Changed:
.github/workflows/ci.yml (windows Test step: added -p no:xdist, updated the T-3540/T-3549 comment block with the round-2 finding)

Evidence:
tests/unit/test_release_workflow_gate.py::TestCiWindowsLegAdvisoryOnly::test_build_job_continue_on_error_is_windows_only (regression coverage, unaffected)
YAML validated with python3 -c "import yaml; yaml.safe_load(...)"
BUG002 waived (cannot repro this class of defect locally, no Windows box) -- see the frob:waive on the ticket body for the full reason.

Gates: frob check --ticket T-3549 --budget 300 clean of ci.yml-attributable errors

### Changed
```
 tickets/T-3549/ticket.md | 17 +++++++++++++++--
 1 file changed, 15 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_release_workflow_gate.py::TestCiWindowsLegAdvisoryOnly::test_build_job_continue_on_error_is_windows_only` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 26 error(s), 4078 warning(s), 895 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV003@tests/system/test_faulthandler_ci_hygiene.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_process_lock.py, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_process_lock.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, SELFAUDIT001@docs/design/registry/capability-via-ratchet.lock.json, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json

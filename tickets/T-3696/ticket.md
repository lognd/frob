---
id: T-3696
title: 'add PLATFORM002: flag os.kill(pid, 0) outside the sanctioned liveness probe'
state: in-progress
kind: bug
origin: human
created: '2026-09-02'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_win32_kill_signal.py
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- docs/modules/gates.md
- tests/unit/gates/test_win32_kill_signal.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: 'Given the new PLATFORM002 AST detector wired into frob check''s gate registry,
    when frob check runs against a fixture file containing os.kill(pid, 0), then it
    reports a PLATFORM002 violation (before: no such rule exists / after: PLATFORM002
    FAILS on the fixture then PASSES once the call is removed or waived) -- production-invocation
    proof per the T-0756 new-gate-rule acceptance policy'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3686 fixed a 20-round win32 debugging saga: an admission pid-liveness probe called os.kill(pid, 0) unconditionally. On win32 CPython, os.kill maps signal 0 to signal.CTRL_C_EVENT (numeric value 0) and implements it via GenerateConsoleCtrlEvent, broadcasting a real Ctrl+C to every process on the caller's console -- including frob check itself. The sanctioned, console-safe liveness probe already exists: frob.process._pid_liveness.pid_alive (OpenProcess/GetExitCodeProcess, query-only rights, never terminates or signals anything). Per this repo's standing perf-findings-become-lint-rules doctrine, ship the root cause as a permanent static detector so this exact mistake shape cannot land again silently. 
Plan: new AST-based gate module (frob.gates._win32_kill_signal), matching the _walk_lint.py/_port_selfcheck.py precedent -- ast.parse + ast.walk, never regex/substring (token-grammar-fixes-never-lexical doctrine). Flag any os.kill(<anything>, 0) call (signal literal integer 0, or the bare name 0 is the only literal shape -- no symbolic zero-valued signal exists in the stdlib) anywhere under src/frob/ EXCEPT src/frob/process/_pid_liveness.py (the one sanctioned implementation, allowlisted by exact relpath with a reason, same shape PORT001's _ALLOWLIST/WALK001's _SELF_EXCLUDED_FILES use). A non-zero-signal os.kill call (real signal delivery, e.g. signal.SIGTERM) must NOT flag. New rule id PLATFORM002 (rides alongside PLATFORM001's existing 'platform footgun' family in docs/modules/gates.md's rule catalog, though implemented in its own module rather than _walk_lint.py to avoid growing that file further past its existing LARGE001 waiver). WARN severity on arrival, matching every other new-detector turn-on precedent in this repo (PORT001, PLATFORM001, SCOPE002) -- promotion to ERROR is a separate later ticket once a burn-down/false-positive measurement exists. Register PLATFORM002 in _KNOWN_GATE_RULES (src/frob/gates/_waive.py) and wire the gate function into a job in src/frob/gates/__init__.py's job-registry (thread or process pool, matching WALK001/PORT001's own repo-wide-scan posture). Document in docs/modules/gates.md's rule catalog table plus a dedicated section alongside PLATFORM001, and update its frob:enumerates member list. Tests: positive (os.kill(p, 0) flags), negative (os.kill(p, signal.SIGTERM) does not), exemption (the same call inside _pid_liveness.py does not flag). Verify via T-0756's new-gate-rule acceptance policy: a bound acceptance criterion with FAIL/PASS markers proving PLATFORM002 fires through frob check itself (production invocation), not just a unit test. Also: while reading src/frob/gates/_fix_engine_shared.py for existing os.kill(pid, 0) occurrences during T-3686 follow-up research, found a SECOND, currently- live win32-unsafe os.kill(pid, 0) call in that module's own _pid_alive helper (T-3526) -- NOT the sanctioned _pid_liveness module, so PLATFORM002 will legitimately flag it. Fixing that call site is out of THIS ticket's scope (a behavior change to gates/_fix_engine_shared.py, not detector work) -- filed as a separate ticket; see that ticket for detail, this ticket's own frob check run may need a scoped frob:waive PLATFORM002 on that pre-existing site referencing the new ticket until it lands.
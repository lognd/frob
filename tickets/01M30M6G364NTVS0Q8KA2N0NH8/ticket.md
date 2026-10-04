+++
id = "01M30M6G364NTVS0Q8KA2N0NH8"
title = "PLATFORM002 new finding: src/frob/worktrees/_disposable_sweep.py:120 os.kill(pid,0) outside sanctioned liveness probe"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-09-21T00:00:02Z"
aliases = ["T-5222"]
scope = ["src/frob/worktrees/_disposable_sweep.py", "src/frob/gates/_win32_kill_signal.py"]
+++

Found while burning down fresh CI run 35654510898, re-verified on current dev tip. tests/unit/gates/test_win32_kill_signal.py::TestPlatform002::test_frob_itself_is_clean fails: src/frob/gates/_win32_kill_signal.py's gate now reports a NEW PLATFORM002 finding at src/frob/worktrees/_disposable_sweep.py:120, os.kill(<pid>, 0) used outside the gate's sanctioned liveness-probe allowlist. Fix: either route this call through the sanctioned liveness-probe helper the gate already recognizes, or waive it with a stated reason if it is genuinely a different, correct use of signal 0 (the gate's own comment at src/frob/gates/_win32_kill_signal.py notes 'genuinely real signal delivery misidentified by this scan' is a known false-positive shape -- confirm which case this is before fixing).

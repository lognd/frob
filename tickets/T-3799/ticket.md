---
id: T-3799
title: resolve PATH executables via shutil.which in gitio.run_argv for win32 PATHEXT
state: in-progress
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gitio.py
- docs/modules/testing.md
- frob.lock
- tests/test_gitio.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/testing.md
  reason: doc update for the win32 argv-resolution addition, plus the frob.lock digest
    ack it required
  actor: logan
  at: '2026-09-05'
- op: add
  glob: frob.lock
  reason: doc update for the win32 argv-resolution addition, plus the frob.lock digest
    ack it required
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/test_gitio.py
  reason: unit tests added for _resolve_win32_executable and run_argv wiring
  actor: logan
  at: '2026-09-05'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Windows CreateProcess only appends .exe to an extensionless argv[0] (never checks the rest of PATHEXT like .bat/.cmd), so any run_argv caller (gh, git, cargo, etc.) that a Windows PATH shadows with a non-.exe shim silently falls through to a different binary further down PATH. Found while diagnosing T-3798 (test_ghio.py's fake-gh test could not shadow a real installed gh.exe on win32). Consider resolving argv[0] via shutil.which() (which honors PATHEXT) before spawning, so scripted/shimmed executables on PATH are found correctly cross-platform.
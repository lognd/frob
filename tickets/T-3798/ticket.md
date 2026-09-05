---
id: T-3798
title: make fake gh preflight integration test spawn on win32
state: queued
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
- tests/test_ghio.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TestPreflightIntegration::test_real_subprocess_seam_against_a_fake_gh_binary writes a #!/bin/sh fake gh script and chmod 0o755's it, then prepends tmp_path to PATH with ':' -- neither works on win32 (no shebang exec, ':' is not the PATH separator, and a bare extensionless file is not resolved as an executable by CreateProcess). Add a win32 .bat/.cmd fake gh variant and use os.pathsep. Part of win32 CI drain.
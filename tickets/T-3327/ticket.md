---
id: T-3327
title: Doctor's tool inventory should account for frob itself vanishing mid-run during
  a global reinstall
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/doctor.py
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
Observed live during T-3276's own land: a coordinator running 'uv tool install --force --reinstall' to upgrade the global frob binary leaves /home/logan/.local/bin/frob briefly ABSENT from PATH (roughly a minute), during which ANY bare 'frob ...' call fails -- not just frob ticket land. This is exactly the class T-3276 built ToolCategory/ExternalToolStatus/scan_external_tools for (a required tool vanishing must be a loud, named failure, not a mystery 'command not found'), but frob's own binary is not itself in _EXTERNAL_TOOLS (checking whether frob is on PATH from inside frob is a bootstrapping problem -- the process already had to resolve frob to start running). Worth a documented line and/or a defensive check in frob doctor's own global_binary_skew/_probe_global_frob_version path (already probes 'frob --version' via shutil.which) noting that a transient PATH absence during a tool reinstall is a known, expected condition, distinct from frob genuinely not being installed -- so a doctor run mid-reinstall reports something more useful than an unexplained absence. Filed per the coordinator's own suggestion while T-3276 was landing (2026-08-29).
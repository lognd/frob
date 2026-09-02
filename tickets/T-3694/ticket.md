---
id: T-3694
title: 'root-write-guard: strip quoted text before ticket-verb match'
state: queued
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/root-write-guard.py
- .claude/hooks/_root_write_guard_lib.py
- .claude/hooks/tests/**
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
root-write-guard.py false-positives on read-only Bash this session: (a) ps aux | grep "frob ticket land" refused as a root write because the frob ticket <verb> matcher matched the QUOTED grep argument as a real command; quoted text is prose, not program (mirror _shellscan.py discipline). (b) cd /abs/scratchpad && gh api ... > relative.log refused because the redirect target relative.log was resolved against the pre-cd cwd instead of the effective cwd after the leading cd chain. Fix both while PRESERVING T-2850 default-deny: a real frob ticket land at command position from root still refused, a real echo x > root_file.txt (relative, no cd) still refused, a real sed -i on a root file still refused. Add regression tests for both false-positive fixes and all true-positive preservations.
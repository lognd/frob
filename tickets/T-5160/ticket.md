---
id: T-5160
title: empty_code_diff_violations _FENCE_RE.search hangs on large real-repo Done report
  bodies
state: queued
kind: bug
origin: human
created: '2026-09-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_empty_diff_close.py
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
found while working T-4641: tests/gates_suite/test_tick.py::TestTick008UnknownLedgerFields::test_real_repo_ledger_is_tick008_clean called the full tickets_gate(root, queue) over this repo's live ~712-ticket queue and stalled past 120s. faulthandler thread dump under a bounded timeout pinpointed the hang inside frob.gates._empty_diff_close.empty_code_diff_violations -> _changed_paths_from_done_report -> _FENCE_RE.search(rest) (src/frob/gates/_empty_diff_close.py:99, pattern at line 65: re.compile(r"```\n(.*?)\n```", re.DOTALL)) -- a non-greedy DOTALL search re-scanning from every start position is O(n^2)-ish over a large Done report body with no closing fence, and this repo's tickets/ tree is 77MB across 700+ tickets, some with very large bodies. This is a genuine hang independent of TICK008 (T-4641's own fix bypasses it by calling _tick008_unknown_ledger_fields(queue) directly instead of the full gate dispatch, out of T-4641's tests/gates_suite/test_tick.py-only scope to fix here). Fix direction: bound the search (a max body length before falling back to "no fence found", or a non-backtracking scan for the literal fence markers via str.find instead of a DOTALL regex).

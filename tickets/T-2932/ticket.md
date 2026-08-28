---
id: T-2932
title: 'frob-suggest: recursive-grep negative pattern misses a scoped command''s own
  2>&1 redirect'
state: done
kind: bug
origin: human
created: '2026-08-25'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/frob-suggest.py
- tests/test_hook_frob_suggest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_hook_frob_suggest.py::test_recursive_grep_stays_quiet_when_scoped_with_a_trailing_redirect
- tests/test_hook_frob_suggest.py::test_recursive_grep_still_fires_unscoped_with_a_trailing_redirect
- tests/test_hook_frob_suggest.py::test_recursive_grep_stays_quiet_when_scoped_to_a_subdirectory
- tests/test_hook_frob_suggest.py::test_recursive_grep_still_fires_unscoped_at_repo_root
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2908's recursive-grep fix added a negative pattern requiring the scoped
subdirectory path token to be immediately followed by a pipe/semicolon/
end-of-string:

    re.compile(r"\s([A-Za-z0-9_][\w.-]*(?:/[A-Za-z0-9_][\w.-]*)+)\s*(?:[|;&]|$)")

This misses the extremely common `2>&1 | ...` shape: a redirect between the
scoped path and the pipe defeats the lookahead, so a genuinely-scoped
command like `grep -rn "foo" src/frob/verify/_watermark.py 2>&1 | head -30`
still blocks even though it cannot walk .venv/.git/worktrees, same as the
already-fixed no-redirect case. Demonstrated directly (both cases run
against the landed T-2908 hook):

    grep -rn "foo" src/frob/verify/_watermark.py                 -> quiet (fixed)
    grep -rn "foo" src/frob/verify/_watermark.py 2>&1 | head -30  -> still BLOCKS

Fix: extend the negative pattern to tolerate an optional redirect
(`2>&1`, `>file`, etc.) between the path token and the pipe/semicolon/EOL,
mirroring how handrolled-floor-count's own gap class comment already
documents this exact "cannot exclude `&` because `2>&1` is nearly always
present" lesson from T-2031.
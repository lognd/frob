---
id: T-4477
title: 'T-4475 follow-up: noqa marker only on the last physical line; mid-run long
  tokens still refuse lands with E501'
state: in-progress
kind: bug
origin: agent
created: '2026-09-14'
priority: critical
parent: T-4410
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fmt_directives.py
- tests/test_gates_fmt_directives.py
- src/frob/tickets/_land_git_ops.py
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
Follow-up to T-4475 (landed 27d8a7539): the canonicalizer appends `# noqa: E501` only to the FINAL physical line of a directive run whose token cannot fit the budget. A run such as `# frob:tests \` / `# tests/ticket_land_suite/test_land_core.py::TestLandChainedCdRootResolution.test_root_equal_to_a_real_linked_worktree_resolves_and_lands \` / `# kind="integration"` keeps the 139-char node id on a MIDDLE physical line (the continuation backslash), gets no noqa there, and the land's own pre-land ruff check refuses the land as NEW E501 -- T-4474's land was refused 2026-09-14 00:23 UTC with 7 such lines in src/frob/tickets/_land.py (3829, 3832, 4257, 4260, pre-existing runs the canonicalizer rewrote) and src/frob/tickets/_land_passenger_identity.py, plus one I001. Every land that touches a file containing a long-token directive run with a trailing `kind=`/`reason=` field is blocked. FIX: in src/frob/gates/_fmt_directives.py, append the noqa marker to EVERY physical line that exceeds the budget after wrapping (not only the last one), placing it after the continuation backslash in a form the directive parser and `_normalize_waive_fragments` already strip (T-4475 made the parser ignore a trailing noqa pragma; verify a mid-run `\  # noqa: E501` round-trips through parse and through `frob format --directives --check` as a no-op, or move the over-limit token to be the last physical line by emitting trailing fields before it -- choose whichever the DSL grammar supports, prove it with tests). Tests: the exact run above canonicalizes to lines that are all E501-clean under `ruff check --select E501`, parse to the same node id and kind, and are idempotent. ACCEPTANCE: `frob format --directives` over src/frob/tickets/_land.py on main followed by `ruff check --select E501 src/frob/tickets/_land.py` reports 0; T-4474 lands. Sprint v0.531.0 (blocks lands).

---
id: T-0827
title: 'docs: README.md command table + count for frob agent (T-0574 DOC005 gap)'
state: dropped
kind: docs
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- README.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-0574 added a real new top-level subcommand, `frob agent` (currently
`frob agent env`), dispatched directly in __main__._dispatch the same way
`frob bind` is. T-0574's own declared scope (src/frob/tickets/_worktree_guard.py,
src/frob/app/agent_runner.py, src/frob/__main__.py, src/frob/scaffold/_managed.py,
docs/guides/agent-playbook.md, tests/test_worktree_guard.py) did not include
README.md or docs/modules/app.md, so this was left undone deliberately per
that ticket's Done report rather than silently expanding scope.

DOC005 (README.md command-table drift-lock) currently fails as a result:

  README.md:0   DOC005: real subcommand `frob agent` has no command-table
                row in README.md -- add one, or the README silently omits
                a real command
  README.md:54  DOC005: README.md claims 31 commands but the live registry
                has 32 -- update the claimed count

Plan: add a `frob agent` row to README.md's command table (short one-line
description, e.g. "Print/export the dispatched-agent guard env
(FROB_WORKTREE/FROB_AGENT) for a worktree"), bump the claimed command count
from 31 to 32, and re-run `frob check --only docanchor` (or the `gates-fast`
group) to confirm DOC005 clears. A `docs/modules/app.md` section for
`frob agent` is optional polish (the `frob:doc` anchors in
src/frob/app/agent_runner.py currently point at the existing `#runners`
anchor, which resolves cleanly) but would be a reasonable companion edit.

## Drop reason
- 2026-07-23: absorbed by T-0574 (scope-added README.md/docs/modules/app.md instead) (absorbed by T-0574)
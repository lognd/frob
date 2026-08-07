---
id: T-1443
title: tickets.md merge driver invokes bare frob, silently running pre-T-1437 splice
  logic under a stale global install
state: done
kind: docs
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- cmd:git config --get merge.frob-ledger.driver exit=0 sha256=5e41d4885016
designated_repro_test: null
threat: null
component: null
---
docs/modules/tickets.md's documented one-time per-clone setup
(docs/modules/tickets.md#git-merge-driver) registers the tickets.md/
tickets-archive.md merge driver as:

    git config merge.frob-ledger.driver "frob ticket merge-driver %O %A %B"

This invokes the BARE `frob` binary, not `uv run frob` -- exactly the
hazard docs/guides/agent-playbook.md section 2 warns about for every
OTHER frob invocation ("Editing src/frob/gates/** ... and then running a
stale globally-installed frob binary silently checks against the OLD gate
logic"). Confirmed live during T-1371's resume (2026-08-02): the globally
installed `frob` in this environment was 0.184.0, predating T-1437's
ledger-splice fix, while the checkout's own pyproject.toml declared
0.293.0. Every `git merge main` in every worktree on this machine
therefore runs the ledger splice under the STALE, pre-T-1437 driver
regardless of how current the checkout's own source is -- reintroducing
exactly the "ledger splice driver resurrects archived tickets, breaking
every in-flight worktree land" defect T-1437 already fixed in source, via
a documented setup step that can never pick up the fix.

Fix: either
(a) change the documented registration command to route through `uv run
frob` (or an absolute path into the checkout's own .venv), or
(b) make `frob ticket merge-driver`'s own entry point version-check
itself against the invoking checkout's pyproject.toml and refuse/warn
loudly on a mismatch, mirroring the WARNING `uv run frob` already prints
in the opposite direction.

(b) is more robust since a stale global `frob` will keep getting
reinstalled/found first in some environments regardless of what the docs
say; consider both.
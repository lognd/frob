---
id: T-2027
title: frob_doable_tickets (serve daemon RPC + MCP tool) bypasses T-2006's dispatch-time
  sweep-ticket revalidation
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/serve/_tools.py
- tests/test_app_daemon_proxy.py
evidence_scope:
- tests/test_serve_tools_daemon_bypass.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_serve_tools_daemon_bypass.py::TestFrobDoableTicketsRevalidation::test_resolved_sweep_ticket_is_dropped_before_listing
- tests/test_serve_tools_daemon_bypass.py::TestFrobDoableTicketsRevalidation::test_still_reproducing_sweep_ticket_stays_listed
- tests/test_serve_tools_daemon_bypass.py::TestFrobDoableTicketsRevalidation::test_no_sweep_tickets_never_calls_revalidate
- tests/test_app_daemon_proxy.py::TestDifferentialParity::test_doable_tickets_json_daemon_matches_in_process
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-2006 wired revalidate_dispatchable_sweep_tickets into
frob.app.ticket_runner._query._doable's in-process render path, but two
OTHER consumers read the exact same doable-tickets data through a
completely different code path that never reaches it, both confirmed
live and reachable, not hypothetical:

MEASURED:

1. frob.serve._tools.frob_doable_tickets (src/frob/serve/_tools.py:78)
   calls doable(queue, root) directly -- the same frob.tickets.doable
   primitive _query._doable calls, but with NO revalidate_dispatchable_
   sweep_tickets call before it, and no reload-after-drop step. Read
   directly: `queue_result = load_queue(root); tickets = doable(queue_
   result.danger_ok, root); return Ok([t.model_dump(...) for t in
   tickets])` -- confirmed no import of, or call to, revalidate_
   dispatchable_sweep_tickets anywhere in this file.

2. This ONE function is the SHARED implementation both the socket daemon
   RPC and the MCP server register verbatim -- not two divergent copies,
   one shared function with two dispatch tables pointing at it:
   - src/frob/serve/_socketd.py:201 -- `_TOOL_DISPATCH = {"frob_doable_
     tickets": _tools.frob_doable_tickets, ...}`, the handler `send_
     request`'s client-side proxy (`frob.app._daemon_proxy.query`,
     called from `_query._try_doable_via_daemon`) talks to over a real
     socket.
   - src/frob/serve/server.py:49 -- `@server.tool() def frob_doable_
     tickets() -> list[dict]: return _unwrap(_tools.frob_doable_
     tickets(root))`, a FastMCP tool registration.

3. The FastMCP path is LIVE in this repo's own config, not merely
   theoretical: `.mcp.json` at the repo root registers `"frob": {"type":
   "stdio", "command": "frob", "args": ["serve"]}` as a project MCP
   server -- any Claude Code session (coordinator or dispatched agent)
   with the frob MCP server enabled gets `frob_doable_tickets` as a
   directly-callable tool, with NO `FROB_DAEMON=1` gate at all (that env
   var only gates the CLI's OWN daemon-proxy fallback,
   `_daemon_proxy._daemon_enabled`, in `_query._try_doable_via_daemon`
   -- the MCP stdio server is a wholly separate entrypoint,
   `frob.serve.server.run_stdio`, that never consults it).

4. The socket-RPC path (consulted from `_query._try_doable_via_daemon`)
   IS gated behind `FROB_DAEMON=1` (`_daemon_proxy._daemon_enabled`,
   opt-in, default off) -- confirmed unset in this session
   (`echo $FROB_DAEMON` -> unset) and not set anywhere in this repo's
   own tooling/config (`git grep FROB_DAEMON` across .py/.md/.toml/.json
   /.claude -> only docs and the T-1379 ticket that introduced the
   opt-in default; zero places that flip it on). No live `frob serve`
   socket daemon process was running at investigation time (`ps aux`
   checked). So THIS specific path is real but currently dormant unless
   an operator explicitly opts in.

NET: one of the two consumers of the un-revalidated `frob_doable_
tickets` (the MCP tool) is live and reachable by any agent with the
project's frob MCP server enabled RIGHT NOW, with no opt-in flag
required; the other (raw socket RPC via the CLI's own `--json` fast
path) is real code but requires an operator to set FROB_DAEMON=1, which
nothing in this repo does today. This is NOT a "should say so and drop
it" case -- the MCP path is a confirmed, unconditional bypass of T-2006's
fix for exactly the automated-consumer audience the fix was meant to
cover.

## Do not fix it this way
- Do NOT remove or disable either fast path (the daemon socket RPC or
  the MCP stdio server) -- both exist for real performance/integration
  reasons unrelated to this gap.
- Do NOT duplicate revalidate_dispatchable_sweep_tickets's logic into
  `frob.serve._tools` or `frob.serve.server` -- a second copy is the
  exact failure class T-1983/T-2006 exist to close (two independent
  places assuming a correspondence the other side can silently violate).
  The fix is ONE new call to the EXISTING function, at the ONE shared
  implementation both dispatch tables already point to
  (`frob.serve._tools.frob_doable_tickets`) -- never a per-consumer
  reimplementation.
- Do NOT gate the fix behind `FROB_DAEMON`/an opt-in flag -- the MCP
  path this ticket found is unconditional; gating the fix the same way
  the daemon-proxy fallback is gated would leave the actually-live path
  uncovered.

## Acceptance criteria
1. `frob.serve._tools.frob_doable_tickets` calls
   `frob.app.ticket_runner._rapid_sweep.revalidate_dispatchable_sweep_
   tickets` on the loaded queue's tickets before computing `doable(...)`,
   reloading the queue if anything was dropped -- mirroring
   `_query._doable`'s own sequence exactly, not a new invention.
2. A test proving the MCP/socket-RPC path drops a resolved sweep-filed
   ticket the SAME way `_query._doable` already does (i.e. a
   differential-parity test: the two code paths must agree on the
   resulting doable set for a resolved sweep-filed ticket, not just each
   independently "look reasonable").
3. `tests/test_app_daemon_proxy.py::TestDifferentialParity` (or the
   nearest existing differential-parity suite for this RPC) is extended
   or already covers this, so a FUTURE divergence between the two call
   sites is caught mechanically, not just fixed once by hand.
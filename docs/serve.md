# frob.serve -- MCP adapter exposing enforcement queries

One sentence: `frob serve` starts a read-only Model Context Protocol (MCP)
server over stdio so any MCP-aware agent can call frob's enforcement
queries directly, instead of shelling out to the CLI and parsing text.

`frob.serve` never mutates tickets, `frob.lock`, or the graph cache; every
tool is a thin, JSON-serializable wrapper around an existing `frob.graph`,
`frob.tickets`, or `frob.gates` read path. The graph snapshot is loaded
cache-first and rebuilt only on a stale/missing cache, same as `frob graph
query`.

## mcp SDK

<!-- frob:describes src/frob/serve/_tools.py::ServeError -->
<!-- frob:describes src/frob/serve/server.py::McpUnavailable -->
<!-- frob:describes src/frob/serve/server.py::build_server -->
<!-- frob:describes src/frob/serve/server.py::run_stdio -->
<!-- frob:describes src/frob/app/serve_runner.py::run -->

Tools live in `frob.serve._tools` as plain functions returning
`Result[dict, ServeError]` (typani), with **no** dependency on the `mcp`
package -- they are directly unit-testable without a transport. The stdio
transport (`frob.serve.server`, built on `mcp.server.fastmcp.FastMCP`)
imports `mcp` lazily, at server-construction time via `build_server` (and
`run_stdio`, which builds then blocks on the stdio loop); a missing `mcp`
package raises `McpUnavailable`. `frob.app.serve_runner.run` (the `frob
serve` CLI entry) catches `McpUnavailable` and prints a clear "mcp SDK not
installed" message, exiting 1, instead of letting the import error propagate.

## Tools

<!-- frob:describes src/frob/serve/_tools.py::frob_doable_tickets -->
<!-- frob:describes src/frob/serve/_tools.py::frob_stale_docs -->
<!-- frob:describes src/frob/serve/_tools.py::frob_check_scope -->
<!-- frob:describes src/frob/serve/_tools.py::frob_graph_query -->
<!-- frob:describes src/frob/serve/_tools.py::frob_doc_for -->

- `frob_doable_tickets()` -- the doable ticket list (id/title/kind),
  oldest-first, mirroring `frob ticket doable`.
- `frob_stale_docs()` -- the drift report: DRIFT001 stale acks (a locked
  digest that moved) and DRIFT002 dangling edges (an edge endpoint that no
  longer resolves), mirroring `frob graph why`'s underlying comparison.
- `frob_check_scope(ticket_id)` -- whether the working diff stays within
  `ticket_id`'s declared `scope` globs (SCOPE001), via `frob.gates.run_gates`
  restricted to the `scope` gate.
- `frob_graph_query(symref)` -- resolve `symref` and list its outgoing and
  incoming obligation-graph edges, mirroring `frob graph query`.
- `frob_doc_for(symref)` -- the `frob:doc` edges `symref` declares and the
  `frob:describes` (markdown doc anchor) edges that describe it.

## CLI

```
frob serve [path]
```

Starts the stdio MCP server rooted at `path` (default `.`). Intended to be
launched by an MCP client (e.g. an editor or agent harness), not run
interactively.

## Deviations

- No write/mutating tools are exposed by design (T-0010's scope is
  enforcement *queries*); `frob ack`, `frob ticket new/transition`, etc.
  remain CLI-only.

# Exhaustive research: the frontier-loop

<!-- frob:ticket T-0185 -->

How to run a "cover everything, no early exit" pass -- audit every module,
read every relevant paper, map an entire subsystem -- without the agent
declaring done having only drained the top of its own context stack.

## The problem this solves

A normal thorough pass keeps its to-do list in the agent's own context. As
context fills, the oldest unexplored branches fall out of attention and the
agent reports "done" having only worked through the first half of what it
enumerated. This is the same failure the review/gate discipline elsewhere
in this repo exists to catch, applied to research instead of code: producer
self-assessment is not evidence.

The fix is architectural, not a bigger prompt: move the frontier out of
context into an external, checkable store, and make "done" mean "the store
has zero pending nodes," never a judgment call.

## Where it lives

- `agents/exhaustive-researcher` -- the agent definition. Wires serena (code
  digestion), the `frob` MCP (ticket graph as the code frontier), and the
  `fetch`/`arxiv` MCP servers (prose/paper retrieval) behind the frontier
  loop.
- `skills/exhaustive-research` -- the reusable skill (`SKILL.md`) any agent
  can load to run the loop: enumerate, drain, prove. This is the operating
  manual; the agent definition just points at it.

## The three phases

1. **Enumerate (breadth, zero depth).** Map the entire top level of the
   tree and write every node to an external store as `pending` before
   exploring anything. Establish a denominator -- the known size of the
   universe -- so "exhaustive" is falsifiable.
2. **Drain.** Loop until zero `pending`: pop one node, explore it in a
   fresh narrow-scope sub-agent, push any children it reveals back onto
   the frontier as `pending`, then mark it `done` with findings recorded
   in the store.
3. **Prove.** An independent verifier (never the producer) reconciles the
   `done` count against the denominator and confirms `done` means
   genuinely explored, not skipped.

See `skills/exhaustive-research/SKILL.md` for the full doctrine and hard
rules.

## Frontier store, by corpus

| Corpus | Store | Retrieval |
|---|---|---|
| This codebase / sibling repos | frob's ticket graph (`frob ticket doable` is the pending query), wired via the `frob` MCP server | `serena` for hierarchical symbol digestion |
| Prose / papers / web | Obsidian vault at `/mnt/c/Users/logan/Documents/Obsidian Notes` (plain markdown, one note per node, frontmatter `status: pending\|done`, backlinks form the tree) | `fetch` MCP (HTML/PDF -> markdown, chunked via `start_index`), `arxiv` MCP (search/download/read papers), WebSearch/WebFetch for discovery |
| Mixed | two frontiers behind one checklist, both required empty before done | both of the above |

**Why the Obsidian vault and not a dedicated graph-memory server:** the
design considered the official `modelcontextprotocol/servers` memory
server, Graphiti + FalkorDB, MegaMem (Obsidian <-> Graphiti), and
Piotr1215/mcp-obsidian. MegaMem was the closest fit conceptually (markdown
vault doubling as human-browsable notes) but is not wired into this
environment's MCP roster. The vault is used directly over the filesystem
instead: it is plain markdown (human-inspectable, git-trackable, no
lock-in) and needs no new server. If a dedicated graph-memory MCP is wired
in later, it slots in behind the same "prose frontier store" role without
changing the skill's phase structure.

## MCP wiring

`.mcp.json` at the repo root declares the servers this workflow depends on,
the same way `agents/*` and `skills/*` depend on the `frob` MCP server for
the ticket graph:

```json
{
  "mcpServers": {
    "serena": { "command": "serena", "args": ["start-mcp-server", "--context", "claude-code", "--project-from-cwd"] },
    "frob":   { "command": "frob", "args": ["serve"] },
    "fetch":  { "command": "uvx", "args": ["mcp-server-fetch"] },
    "arxiv":  { "command": "arxiv-mcp-server", "args": [] }
  }
}
```

`serena` and `frob` are already required by the rest of the agentic
workflow (see `docs/guides/agentic-workflow.md`); `fetch` and `arxiv` are
additive, needed only for the prose/paper corpus.

## Priors

The design draws on two externalization/memory papers, retrievable via the
`arxiv` MCP:

- `2604.08224` -- survey of context externalization strategies for
  long-horizon agents (why frontier-in-context degrades as context fills).
- `2604.11243` -- self-evolving knowledge wikis (why a durable, node-level
  external store outperforms re-deriving state each pass).

## Running it

```text
Use the exhaustive-research skill (or dispatch agents/exhaustive-researcher)
for: <the thing that needs total coverage>
```

The report at the end always leads with honesty: denominator, nodes done,
nodes blocked (and why), and the Phase-2 coverage verdict. A pending or
blocked count is stated in the first sentence, never rounded up to "done."

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

## What belongs to this repo

This page documents a METHOD and one concrete mechanism this repo ships:
the corpus-emit path (T-0429, below), which `frob.registry._corpus` and
`frob.app.registry_runner` bind to by `frob:doc` anchor.

No harness agent or skill definition is versioned here. Any such definition
is operator configuration and lives at user scope; a project-scope copy
shadows it and the two drift apart unnoticed, which is exactly what happened
before the repo copies were removed. The `docs/design/*-corpus.md` files
record this method as their provenance -- that provenance is a fact about
how they were built and is deliberately left in place.

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

See `~/.claude/skills/exhaustive-research/SKILL.md` for the full doctrine and
hard rules.

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
the same way the dispatched agents and skills depend on the `frob` MCP server for
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

## Corpus-emit mechanism (T-0429)

The frontier store above (frob tickets / Obsidian vault) is where a
research pass tracks its OWN progress. It is not, by itself, the
`docs/design/registry/*.yaml` universe corpus the exhaustiveness gate
(`frob.gates._registry_exhaustiveness`) actually reads -- a finding that
only ever lands in the vault is exactly the "orphaned docs" failure mode
T-0343/T-0424 named for the registry itself, one layer upstream. This
section closes that gap: the mechanical path from "research found N
things" to "the corpus contains N new entries", so nothing is left as
untranscribed prose.

**Schema.** Every registry entry (`frob.registry.RegistryEntry`) is:
`id` (a stable, file-namespaced string, e.g. `PAT-TRAP-07-REPOSITORY`),
`name`, an optional `source_doc` citation, `disposition` (a researcher-
emitted entry is ALWAYS `"pending"` -- see below), and `cross_refs`
(empty at emit time). This is the same shape every existing registry
file already carries; a research pass does not invent a new shape per
corpus.

**Emit tool.** `frob registry add --file <name.yaml> --key <entries-key>
--id <ID> --name "<name>" [--source-doc <doc>]` appends one such entry
directly to the named file under `docs/design/registry/`
(`frob.registry.append_entry`) -- a research pass writes into the SSOT
itself, never a side document that later needs hand-transcription. It
rejects a duplicate id before writing (fail-fast; the exhaustiveness
gate's REG007 re-verifies this on the next `frob check` regardless).

**Denominator proof.** Registry files may declare a `total:` (or
`<prefix>_total:` for a split entry-list key) alongside their entries;
`append_entry` bumps that count in lockstep with every append, so REG005
(`frob.gates._registry_exhaustiveness`) -- which fails a file whose
declared total drifts from its actual entry count -- is the exhaustiveness
gate a research pass's own declared enumeration total is checked against.
A research pass that says "I enumerated 41" and appends 41 entries to a
file declaring `total: 41` has a machine-verified denominator, not a
self-report.

**Failure modes.** `append_entry`'s `CorpusError` (`frob.registry._corpus`)
covers file-absent (`FileNotFound`), key-absent (`KeyNotFound`),
already-present (`DuplicateId`), and write-failed (`WriteFailed`, T-1533)
-- the last one dedicated to an `atomic_write` I/O failure, distinct from
the file simply not existing, so a caller keying a message dict on
`CorpusError` never has to guess which case actually happened.

**No dispositions at emit time.** Under the derived-registry model
(T-0428: `handled_by` is cross-checked against code-declared
`frob:enforces`, never authored by hand), the researcher's job stops at
enumeration -- every emitted entry is `disposition: "pending"`. A later
code change adding `frob:enforces <that-id>` to the rule that actually
covers it is what makes the entry's eventual `handled_by:<rule>`
disposition honest; a reviewer or a follow-up ticket handles
`deferred:`/`out_of_scope:` for the rest. The researcher never
short-circuits this by writing a disposition it cannot verify.

## Priors

The design draws on two externalization/memory papers, retrievable via the
`arxiv` MCP:

- `2604.08224` -- survey of context externalization strategies for
  long-horizon agents (why frontier-in-context degrades as context fills).
- `2604.11243` -- self-evolving knowledge wikis (why a durable, node-level
  external store outperforms re-deriving state each pass).

## Running it

```text
Run the frontier loop below (enumerate, drain, prove)
for: <the thing that needs total coverage>
```

The report at the end always leads with honesty: denominator, nodes done,
nodes blocked (and why), and the Phase-2 coverage verdict. A pending or
blocked count is stated in the first sentence, never rounded up to "done."

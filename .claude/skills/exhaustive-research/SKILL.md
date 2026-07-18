---
name: exhaustive-research
description: Research or map something to genuine completeness without exiting early. Use when a task needs EVERYTHING covered -- audit every module, enumerate every case, read every relevant paper/doc, map an entire subsystem -- and a normal pass would drain only the top of the stack. Externalizes the frontier so completeness is a checkable fact, not a feeling.
---

<!-- frob:doc docs/guides/exhaustive-research.md#exhaustive-research-the-frontier-loop -->

# exhaustive-research

Early exit is the default failure of "be thorough" tasks: the list of
things still to explore lives in the agent's context, so as context fills
the oldest branches fall out of attention and the agent declares done
having drained only the top of the stack. This skill removes that failure
by moving the frontier OUT of context and tying completion to the frontier
being provably empty.

Core doctrine (the vacuous-pass rule applied to research): **"I found
nothing more" is only valid when backed by an empty enumerated frontier,
never by the agent stopping.** If you cannot point at an external store
with zero pending items, you are not done.

## The three phases -- do them in order, never skip Phase 0

### Phase 0 -- Enumerate the universe (breadth, ZERO depth)

Before exploring anything, enumerate the entire top level of the tree and
write every node to an EXTERNAL store as `pending`. Do not follow the first
interesting branch. Mapping the whole shape first is the antidote to
depth-first drift.

Also establish a **denominator**: the known size of the universe (N modules,
N files, N papers in the corpus, N catalog entries). Without a denominator,
"exhaustive" is unfalsifiable -- you cannot know you missed something if
nothing tells you the total. If the corpus has no natural count, enumerate
until the enumeration itself is closed (no source names a node you haven't
listed).

### Phase 1 -- Drain the frontier

Loop until the store has zero `pending`:
1. Pop one `pending` node.
2. Explore it in a FRESH, NARROW-SCOPE sub-agent (one node's worth of
   context, not the whole tree). The orchestrator holds only the frontier;
   findings live in the store.
3. Append any children the node reveals back onto the frontier as `pending`
   BEFORE marking the node `done`. This is what makes the loop actually
   exhaustive -- discovered work re-enters the queue instead of being lost.
4. Mark the node `done` with its findings recorded in the store.

Termination is a checkable fact: `pending == 0`, not a judgment call.

### Phase 2 -- Prove coverage

Dispatch an INDEPENDENT verifier (not the producer) that confirms every
enumerated node reached `done`, that `done` means genuinely explored and
not skipped, and that the count of `done` nodes matches the Phase 0
denominator. Producer-grades-own-work collapses under context pressure;
the split is the same discipline that catches every real defect in review.

## The external store -- pick by corpus

- **Code** (this repo or siblings): use frob's ticket graph as the frontier
  -- it is already a git-tracked store with `pending`/`done` states,
  blockers, and a `frob ticket doable` query. Enumerate nodes as tickets (or
  a scratch checklist for a lighter sweep); use serena to digest code
  hierarchically (symbol overview first, then drill in).
- **Prose / papers / web**: use the Obsidian vault at
  `/mnt/c/Users/logan/Documents/Obsidian Notes` via the filesystem as the
  frontier + findings store -- one note per node, frontmatter `status:
  pending|done`, backlinks for the tree. (NOT MegaMem -- it is not wired.)
  Retrieval: the `fetch` MCP (HTML/PDF -> markdown, chunked via start_index
  so you read a long source in pieces), the `arxiv` MCP (search + download +
  markdown for papers), and WebSearch/WebFetch for discovery. Always record
  the corpus size so the denominator holds.
- **Mixed** (e.g. "every dangerous operation across every stdlib"): run two
  frontiers behind one checklist -- code nodes in the ticket graph, external
  reference nodes in the vault -- and require BOTH empty before done.

## Hard rules

- Never explore before Phase 0 is complete. Breadth first, always.
- Never mark the whole task done while any node is `pending`. Report the
  pending count if you must stop early -- do not round it to "done."
- Never let one context hold the whole tree. Fresh sub-agent per node.
- Always record the denominator and reconcile `done` against it in Phase 2.
- A node you could not explore is `blocked`, not `done` -- surface it, never
  silently drop it.

## Reporting

End with: denominator (universe size), nodes done, nodes blocked (and why),
and the Phase-2 coverage verdict. If anything is blocked or pending, say so
in the first sentence -- the whole point of this skill is that "done" is
honest.

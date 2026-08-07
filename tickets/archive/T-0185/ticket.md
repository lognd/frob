---
id: T-0185
title: 'exhaustive-research agent: frontier-loop with external graph-knowledge store'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- .claude/skills/**
- .claude/agents/**
- .mcp.json
- docs/guides/**
- tickets.md
- tests/unit/test_research_assets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_research_assets.py::test_mcp_json_parses_and_declares_required_servers
- tests/unit/test_research_assets.py::test_skill_frob_doc_anchor_resolves_in_guide
designated_repro_test: null
threat: null
component: null
---
An exhaustiveness-research capability whose stop condition is a provably
empty frontier, not the agent feeling done. Root cause of early exit
(observed repeatedly this session): the frontier lives in agent context,
so as context fills the oldest unexplored branches fall out of attention
and the agent declares done having only drained the top of the stack
(the original "we only pop the top half" problem). Fix is architectural,
not a bigger prompt.

Design: a frontier-loop skill any agent can run, backed by an EXTERNAL
frontier store.
Phase 0 (breadth, no depth): enumerate the entire top-level tree and
write every node to the store as pending BEFORE exploring any node.
Phase 1 (drain): pop one pending item, explore it in a fresh narrow-scope
sub-agent, append any children it reveals back onto the frontier, mark
done. Loop terminates only when zero pending remain -- a checkable fact.
Phase 2 (coverage proof): an independent verifier confirms every
enumerated node reached done and spot-checks that done means explored,
not skipped (producer/verifier split, the same discipline that caught
every REJECT this session). Vacuous-pass doctrine applied to research:
"found nothing more" must be backed by an empty enumerated frontier,
never by the agent stopping.

Frontier store options by corpus (user wants all three corpora: this
codebase + siblings, external docs/web, mixed):
- CODE: frob's own ticket graph via frob serve (now MCP-wired) is already
  a git-tracked frontier with blockers and a doable query -- use it; plus
  serena for hierarchical symbol digestion.
- EXTERNAL/PROSE: a graph-knowledge memory MCP so the frontier and
  findings survive context resets. 2026 survey (verify at build): the
  official modelcontextprotocol/servers "memory" server (entities+
  relations knowledge graph, Anthropic-maintained, simplest); Graphiti +
  FalkorDB (getzep/graphiti -- temporal graph, group_id tenant isolation,
  production-grade); MegaMem (Obsidian vault <-> Graphiti temporal graph,
  12 graph tools + 11 vault file tools, markdown-native so it doubles as
  human-browsable notes -- best fit for the "Obsidian-style" request);
  Piotr1215/mcp-obsidian (simple local-vault read/write); Cognee/Smriti
  (document-ingest graph extraction with conflict detection). Obsidian is
  attractive because the store is plain markdown -- human-inspectable,
  git-trackable, no lock-in.
- DENOMINATOR: retrieval must report a known corpus size (N docs, K read)
  so exhaustiveness has a denominator to check against; without it
  "exhaustive" is unfalsifiable.

Deliverables: (1) the frontier-loop as a reusable skill under
.claude/skills; (2) a frontier-store adapter abstraction so code uses the
ticket graph and prose uses the chosen graph-memory MCP behind one
interface; (3) an exhaustive-researcher agent definition wiring serena +
the graph-memory MCP + web retrieval, with the hard gate "frontier
nonempty => not done" and a coverage-proof verifier pass; (4) evaluate
and pin the specific MCP servers above (spike MegaMem/Obsidian and the
official memory server, pick one, document why) -- .mcp.json entries and
setup docs like the serena/frob wiring; (5) reference arxiv priors on
agent externalization/memory (2604.08224 externalization review;
2604.11243 self-evolving knowledge wikis) in the design doc.
ASCII only, no emojis.
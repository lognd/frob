## Done report

Changed: commit 22654d4 (pre-ticket-start) landed the skill
(.claude/skills/exhaustive-research/SKILL.md) and agent
(.claude/agents/exhaustive-researcher.md); this ticket's remainder landed
.mcp.json (serena/frob/fetch/arxiv stdio servers -- the repo had no MCP
pinning at all), docs/guides/exhaustive-research.md (setup guide: three
phases, store-per-corpus table, Obsidian-vault-over-MegaMem decision,
.mcp.json wiring, the two arxiv priors), a frob:doc edge from SKILL.md to
the guide anchor, and tests/unit/test_research_assets.py as a drift-lock
(mcp config parses and declares the four servers; the SKILL.md anchor
resolves in the guide).

Evidence:
tests/unit/test_research_assets.py::test_mcp_json_parses_and_declares_required_servers
tests/unit/test_research_assets.py::test_skill_frob_doc_anchor_resolves_in_guide

Filed: T-0186 (docs/index.md link, DOC001 -- index was outside this
ticket's scope), landed in the same merge so main's gate never went red.
Gates: 41 violations reported in the worktree, 40 pre-existing and none
touching this diff's surface (DRIFT002 self-model x26, COV003
T-0065/T-0148 x12, SYS004+TEST006 worktree-native artifacts); the one
diff-caused DOC001 resolved by T-0186.
Review: one REJECT round (gate-report phrasing overstated as "clean
except DOC001"; landing-state confusion); corrected per coordinator.

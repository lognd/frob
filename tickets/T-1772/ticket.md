---
id: T-1772
title: 'Delete root agents/ and skills/: nothing reads them, the real load path is
  ~/.claude'
state: queued
kind: feature
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- agents/**
- skills/**
- docs/guides/agentic-workflow.md
- docs/guides/exhaustive-research.md
- docs/modules/testing.md
- src/frob/_cli_parsers/_ticket/_query.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Root `agents/` and `skills/` (13 tracked SKILL.md files) are dead weight
and are deleted here.

T-1767's audit concluded KEEP, reporting them "empirically confirmed
live-read by the dispatching harness, not orphaned". That conclusion was
wrong, and the verification that produced it was the trap: the agent
names in `agents/` (implementer, debugger, planner, reviewer, prover,
interface-auditor, security-auditor) DO match agents that dispatch
successfully, so seeing both facts together reads as proof of a link that
is not there.

Checked directly instead:

- No Python code reads either directory. A grep for `"agents/`,
  `'agents/`, `Path("agents")` and the `skills/` equivalents across
  `src/frob/**` returns nothing.
- Neither is packaged: `pyproject.toml` ships `packages = { find = {
  where = ["src"] } }` only.
- `frob scaffold` does not emit them; `src/frob/scaffold/data/` holds
  only `shared/` and `types/`.
- The agents that actually dispatch load from `~/.claude/agents/` (12
  entries, including implementer.md, debugger, planner, reviewer,
  prover, interface-auditor, security-auditor) and the skills from
  `~/.claude/skills/` (audit, audit-fix, develop, document,
  exhaustive-research, fix, next, plan). The repo's own `.claude/agents/`
  holds one file, `exhaustive-researcher.md`. Repo root is not on any
  load path.

So the directories were duplicate copies of user-scope definitions,
tracked in git, that nothing read. CLAUDE.md's opening section already
called for their removal or rework; the owner confirmed removal.

Docs referencing them are rewritten rather than deleted, because the
WORKFLOW they describe is real even though the paths were not:
`docs/guides/agentic-workflow.md` now points at `~/.claude/agents/*` and
`.claude/agents/*` as the actual load path and refers to skills by their
invocation name (`/next`, `/plan`, `/audit`, `/prove`) instead of a
directory that no longer exists; `docs/modules/testing.md` and
`docs/guides/exhaustive-research.md` likewise. The doc-anchor comment in
`_cli_parsers/_ticket/_query.py` is repointed to the renamed anchors.

`docs/rework.md` and `docs/index.md` keep their references untouched --
both are historical records of a past purge and redesign, and rewriting
history to match the present would destroy the thing they exist for.

LESSON WORTH KEEPING, and the reason this ticket exists separately rather
than as a silent cleanup: "the names match" is not evidence of wiring.
The same shape has now produced three wrong conclusions in this repo -- a
registry read by no code presented as implemented, SYS109 landing as a
tested detector wired into no gate, and this. The check that settles it
is always the same: find the code that reads it, or accept that nothing
does.

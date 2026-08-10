---
id: T-1941
title: 'COV003: T-0185 evidence references a test deleted by the exhaustive-research
  skill/agent removal'
state: queued
kind: bug
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tickets/T-0185/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1933's land-parity check (repo root main, tree at 92320e002) found COV003 firing repo-wide: T-0185's bound evidence 'tests/unit/test_research_assets.py::test_skill_frob_doc_anchor_resolves_in_guide' no longer resolves to a collected test. Root cause looks like commit 72902adc0 ('chore: remove project-scope .claude/agents and .claude/skills'), which deleted the exhaustive-research skill/agent this test exercised, without updating T-0185's evidence. Confirmed reproducing from a clean main checkout with no other changes -- not introduced by T-1933 (scope: docs/design/cli-hygiene.md, docs/index.md, src/frob/app/ticket_runner/_close_cmd.py, src/frob/app/ticket_runner/_new.py). Fix: either restore/replace T-0185's evidence with a currently-collecting test, or if the skill/agent removal genuinely obsoletes what T-0185 verified, re-scope T-0185 and record fresh evidence.
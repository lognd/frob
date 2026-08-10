---
id: T-1941
title: 'COV003: T-0185 evidence references a test deleted by the exhaustive-research
  skill/agent removal'
state: done
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
- tickets/T-1351/**
- tickets/T-1507/**
- tickets/T-1512/**
- tickets/archive/T-0185/**
- tickets/archive/T-1351/**
- tickets/archive/T-1507/**
- tickets/archive/T-1512/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets/T-1351/**
  reason: 'Widening to cover three more COV003 orphans caused by the same class of

    defect (evidence node deleted/replaced by another ticket''s land without

    updating the orphaned ticket''s bound evidence): T-1351, T-1507, T-1512 all

    point at tests/unit/test_check.py::TestScopeDisclosure::test_full_unfiltered_run_adds_no_disclosure,

    which T-1928''s land (e68f129b115f) replaced with

    test_full_run_discloses_fmt_scope (asserting the opposite behavior).

    Per coordinator instruction, fixing all four unticketed/ticketed orphans

    under one series rather than filing duplicate tickets.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-1507/**
  reason: 'Widening to cover three more COV003 orphans caused by the same class of

    defect (evidence node deleted/replaced by another ticket''s land without

    updating the orphaned ticket''s bound evidence): T-1351, T-1507, T-1512 all

    point at tests/unit/test_check.py::TestScopeDisclosure::test_full_unfiltered_run_adds_no_disclosure,

    which T-1928''s land (e68f129b115f) replaced with

    test_full_run_discloses_fmt_scope (asserting the opposite behavior).

    Per coordinator instruction, fixing all four unticketed/ticketed orphans

    under one series rather than filing duplicate tickets.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-1512/**
  reason: 'Widening to cover three more COV003 orphans caused by the same class of

    defect (evidence node deleted/replaced by another ticket''s land without

    updating the orphaned ticket''s bound evidence): T-1351, T-1507, T-1512 all

    point at tests/unit/test_check.py::TestScopeDisclosure::test_full_unfiltered_run_adds_no_disclosure,

    which T-1928''s land (e68f129b115f) replaced with

    test_full_run_discloses_fmt_scope (asserting the opposite behavior).

    Per coordinator instruction, fixing all four unticketed/ticketed orphans

    under one series rather than filing duplicate tickets.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/archive/T-0185/**
  reason: 'The evidence --replace edits for T-1351/T-1507/T-1512 and T-0185 write

    to tickets/archive/T-XXXX/ticket.md for archived tickets (frob ticket

    evidence --archived targets that path), not tickets/T-XXXX/**. Adding

    the archive paths so gate:SCOPE reflects the files this fix actually

    touched.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/archive/T-1351/**
  reason: 'The evidence --replace edits for T-1351/T-1507/T-1512 and T-0185 write

    to tickets/archive/T-XXXX/ticket.md for archived tickets (frob ticket

    evidence --archived targets that path), not tickets/T-XXXX/**. Adding

    the archive paths so gate:SCOPE reflects the files this fix actually

    touched.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/archive/T-1507/**
  reason: 'The evidence --replace edits for T-1351/T-1507/T-1512 and T-0185 write

    to tickets/archive/T-XXXX/ticket.md for archived tickets (frob ticket

    evidence --archived targets that path), not tickets/T-XXXX/**. Adding

    the archive paths so gate:SCOPE reflects the files this fix actually

    touched.

    '
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/archive/T-1512/**
  reason: 'The evidence --replace edits for T-1351/T-1507/T-1512 and T-0185 write

    to tickets/archive/T-XXXX/ticket.md for archived tickets (frob ticket

    evidence --archived targets that path), not tickets/T-XXXX/**. Adding

    the archive paths so gate:SCOPE reflects the files this fix actually

    touched.

    '
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_research_assets.py::test_docs_index_links_the_guide
- tests/unit/test_check.py::TestScopeDisclosure::test_no_disclosure_when_fmt_did_not_run
- tests/unit/test_check.py::TestScopeDisclosure::test_full_run_discloses_fmt_scope
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1933's land-parity check (repo root main, tree at 92320e002) found COV003 firing repo-wide: T-0185's bound evidence 'tests/unit/test_research_assets.py::test_skill_frob_doc_anchor_resolves_in_guide' no longer resolves to a collected test. Root cause looks like commit 72902adc0 ('chore: remove project-scope .claude/agents and .claude/skills'), which deleted the exhaustive-research skill/agent this test exercised, without updating T-0185's evidence. Confirmed reproducing from a clean main checkout with no other changes -- not introduced by T-1933 (scope: docs/design/cli-hygiene.md, docs/index.md, src/frob/app/ticket_runner/_close_cmd.py, src/frob/app/ticket_runner/_new.py). Fix: either restore/replace T-0185's evidence with a currently-collecting test, or if the skill/agent removal genuinely obsoletes what T-0185 verified, re-scope T-0185 and record fresh evidence.
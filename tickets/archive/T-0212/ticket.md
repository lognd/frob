---
id: T-0212
title: DOC002 slugger disagrees with GitHub anchor algorithm in both directions
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/docs/**
- src/frob/strata/_ast.py
- src/frob/strata/_compliance.py
- src/frob/strata/_deploy.py
- src/frob/strata/_infra.py
- src/frob/strata/_lint.py
- src/frob/strata/_models.py
- src/frob/strata/_pii.py
- src/frob/policy/_models.py
- tests/**
- docs/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph.py::TestSlugify::test_lowercases_and_strips_disallowed_punctuation
- tests/test_graph.py::TestMarkdownAnchors::test_describes_edge_with_heading_slug_and_facet
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 lograder (7 DOC002 errors, most error-prone adoption step): 'Output & layouts' -> GitHub #output--layouts vs frob #output-layouts; 'Public/Private Boundary' -> GitHub #publicprivate-boundary vs frob #public-private-boundary. Punctuation runs collapse differently, so anchors satisfying DOC002 can 404 on GitHub and vice versa. Fix: implement GitHub's slug algorithm exactly (test against a table of tricky headings) or accept both forms; T-0165's nearest-anchor suggestions must use the corrected slugs.

Scope widened 2026-07-18 (coordinator directive, post-review): the 46
DOC002 anchors in src/frob/strata/{_ast,_compliance,_deploy,_infra,_lint,
_models,_pii}.py and src/frob/policy/_models.py are a direct mechanical
consequence of this ticket's slugify rewrite and only resolvable with
this branch's slugger present, so they land in the same motion instead of
a separate follow-up ticket. The originally-not filed T-draft-2327479e (never refiled) is
folded into this ticket and dropped from the ledger (see Done report).
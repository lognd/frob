---
id: T-0741
title: 'tickets: disposition TICK006''s ~97 historical T-draft-* phantom-filing findings
  (pre-T-0577 draft-loss residue)'
state: dropped
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
- tickets-archive.md
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-0726 shipped TICK006 (a Done report's affirmative filing claim whose id resolves to no ledger block is now an ERROR). Run cold against this repo's real ledger, it correctly fires on ~97 distinct pre-T-0577 Done reports whose Filed:/filed-as claim named a T-draft-<hex> id that never survived land (the T-0577 draft-loss bug, itself already DONE/fixed for future filings, but never backfilled against its own historical damage) plus was traced to one genuine ledger-corruption case (T-0367 missing its marker, fixed directly in T-0726's own pass; see that ticket's Done report). These ~97 remain unwaived on main today because per-instance frob:waive precision is not currently reachable for tickets.md-anchored violations: TICK006's Violation carries no symref (matching T-0726's sibling TICK003/TICK004 file-scoped convention), so _match_waiver's only available mode for it is a bare-file match on tickets.md -- and a single frob:waive TICK006 placed anywhere in tickets.md would blanket-suppress EVERY current and FUTURE TICK006 finding in the whole file (the exact T-0148 blanket-waiver shape this repo's waiver design otherwise forbids), defeating the gate's entire purpose. Do ONE of: (a) extend TICK006 to set a per-ticket symref (e.g. tickets.md::T-XXXX) AND teach the markdown directive parser (frob.graph.dsl) to bind a frob:waive comment placed inside a ticket's own body to that ticket's symref (not just nearest heading), enabling genuine per-instance waivers; or (b) backfill each of the 97 Done reports with a corrective NOTE (the same disclosure shape already used elsewhere in this ledger for T-0570/T-0332/T-0261/T-0388/T-0177/T-0401's own dangling drafts: 'Done report references T-draft-X; the draft did not survive land (T-0577), never materialized') so the claim is no longer read as an unqualified affirmative filing (TICK006's negation/description-only carve-outs would then apply). Either resolves the debt without weakening TICK006 going forward. The full 97-id list is reproducible via: uv run frob check --only tickets (grep TICK006).

## Drop reason
- 2026-07-22: disposition work absorbed directly into T-0726's own pass: all 97 historical TICK006 phantom-filing findings dispositioned (10 rewritten to their real successor id, 87 negation-annotated) via a scripted, ledger-parse-verified pass over tickets.md/tickets-archive.md; frob check --only tickets now reports 0 TICK006 errors -- no residual disposition work remains to track separately (absorbed by T-0726)
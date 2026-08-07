---
id: T-0691
title: 'decision: next language-adapter tier (Go, Java, C#) -- demand-driven per estate
  + TIOBE/Innovation Graph'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: low
parent: T-0329
tier: ticket
sprint: null
scope:
- docs/design/**
- docs/index.md
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/index.md
  reason: 'DOC001 requires the new docs/design/language-adapter-tier-decision.md to

    be linked from somewhere (frob:describes anchor, frob:doc edge, or a

    markdown link crawled from docs/index.md). Every existing docs/design/*.md

    file is registered the same way, as a bullet in docs/index.md''s Design

    research corpora section. Adding this ticket''s own single new-doc bullet

    there is the minimal mechanical registration needed to keep the ticket''s

    own deliverable gate-clean, not unrelated out-of-scope work.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/integration/test_interfaces.py
  reason: docs-only decision ticket; CLI-dispatch integration test is the T-0167-precedent
    evidence, scope-added for covers_scope (D-02 route 2)
  actor: logan
  at: '2026-07-23'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
acceptance:
- text: GIVEN the estate language survey WHEN this ticket closes THEN docs/design
    records the chosen next adapter tier with rationale and per-language tickets exist
    for chosen languages only
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
---
User question 2026-07-22: should we expand supported languages per github.com Innovation Graph global metrics and the TIOBE index? Current coverage: Python, TypeScript/JS, Rust, C, C++ (+ Kotlin grammar wired, adapter pending T-0614). By both indexes the largest uncovered languages are Java, Go, C#, then PHP/Ruby/Swift. RECOMMENDATION recorded here: expand DEMAND-DRIVEN, not index-driven -- the adapter protocol (T-0609) makes each language a bounded ~1-session ticket, so speculative adapters are cheap to add when a real repo in the estate (or a user project) needs one, and unexercised adapters are exactly the catalogued-but-unenforced dead weight this repo's doctrine forbids. This DECISION ticket closes by recording the chosen next tier (or explicitly none-for-now) in docs/design/ after checking the 9-repo estate's actual language mix; implementation tickets get filed per language only when chosen.
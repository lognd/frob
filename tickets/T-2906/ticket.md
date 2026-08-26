---
id: T-2906
title: wire bash+csharp into frob.vet/frob.dup/frob.gates._docblocks (capability/dup/docblock
  facets)
state: in-progress
kind: docs
origin: human
created: '2026-08-25'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/_support.py
- src/frob/vet/_capability_registry/*.py
- src/frob/dup/_exhaustiveness.py
- src/frob/gates/_docblocks*.py
- tests/test_capability_registry.py
- tests/test_dup_exhaustiveness.py
- tests/test_gates.py
- tests/test_lang_support.py
- tests/fixtures/lang/*
- docs/modules/dup.md
- docs/modules/vet.md
- docs/modules/gates.md
- docs/modules/lang.md
- docs/guides/extending/capability-registry.md
- src/frob/vet/_capability_core.py
- src/frob/vet/_capability_scan.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_capability_registry/*.py
  reason: 'Ticket body requires real subsystem integration in frob.vet._capability_registry,
    frob.dup._exhaustiveness, and frob.gates._docblocks (option a), not just the citation
    (option b) already landed by T-1604/T-1600. Widening from the ticket''s declared
    lang/_support.py-only scope to the exact consumer files that must change for real
    wiring, plus their tests and the existing bash/csharp fixtures.

    '
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/dup/_exhaustiveness.py
  reason: 'Ticket body requires real subsystem integration in frob.vet._capability_registry,
    frob.dup._exhaustiveness, and frob.gates._docblocks (option a), not just the citation
    (option b) already landed by T-1604/T-1600. Widening from the ticket''s declared
    lang/_support.py-only scope to the exact consumer files that must change for real
    wiring, plus their tests and the existing bash/csharp fixtures.

    '
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/gates/_docblocks*.py
  reason: 'Ticket body requires real subsystem integration in frob.vet._capability_registry,
    frob.dup._exhaustiveness, and frob.gates._docblocks (option a), not just the citation
    (option b) already landed by T-1604/T-1600. Widening from the ticket''s declared
    lang/_support.py-only scope to the exact consumer files that must change for real
    wiring, plus their tests and the existing bash/csharp fixtures.

    '
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/test_capability_registry.py
  reason: 'Ticket body requires real subsystem integration in frob.vet._capability_registry,
    frob.dup._exhaustiveness, and frob.gates._docblocks (option a), not just the citation
    (option b) already landed by T-1604/T-1600. Widening from the ticket''s declared
    lang/_support.py-only scope to the exact consumer files that must change for real
    wiring, plus their tests and the existing bash/csharp fixtures.

    '
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/test_dup_exhaustiveness.py
  reason: 'Ticket body requires real subsystem integration in frob.vet._capability_registry,
    frob.dup._exhaustiveness, and frob.gates._docblocks (option a), not just the citation
    (option b) already landed by T-1604/T-1600. Widening from the ticket''s declared
    lang/_support.py-only scope to the exact consumer files that must change for real
    wiring, plus their tests and the existing bash/csharp fixtures.

    '
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/test_gates.py
  reason: 'Ticket body requires real subsystem integration in frob.vet._capability_registry,
    frob.dup._exhaustiveness, and frob.gates._docblocks (option a), not just the citation
    (option b) already landed by T-1604/T-1600. Widening from the ticket''s declared
    lang/_support.py-only scope to the exact consumer files that must change for real
    wiring, plus their tests and the existing bash/csharp fixtures.

    '
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/test_lang_support.py
  reason: 'Ticket body requires real subsystem integration in frob.vet._capability_registry,
    frob.dup._exhaustiveness, and frob.gates._docblocks (option a), not just the citation
    (option b) already landed by T-1604/T-1600. Widening from the ticket''s declared
    lang/_support.py-only scope to the exact consumer files that must change for real
    wiring, plus their tests and the existing bash/csharp fixtures.

    '
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/fixtures/lang/*
  reason: 'Ticket body requires real subsystem integration in frob.vet._capability_registry,
    frob.dup._exhaustiveness, and frob.gates._docblocks (option a), not just the citation
    (option b) already landed by T-1604/T-1600. Widening from the ticket''s declared
    lang/_support.py-only scope to the exact consumer files that must change for real
    wiring, plus their tests and the existing bash/csharp fixtures.

    '
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/modules/dup.md
  reason: docs for the modules whose registries change
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/modules/vet.md
  reason: docs for the modules whose registries change
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/modules/gates.md
  reason: docs for the modules whose registries change
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/modules/lang.md
  reason: docs for the modules whose registries change
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/guides/extending/capability-registry.md
  reason: capability registry extension guide
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/vet/_capability_core.py
  reason: extension->language table and scan-file lang detection live here, needed
    for real bash/csharp reachability
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/vet/_capability_scan.py
  reason: extension->language table and scan-file lang detection live here, needed
    for real bash/csharp reachability
  actor: logan
  at: '2026-08-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1604 (bash) and T-1600 (csharp) each registered a real frob.lang
grammar/walker, but neither wired the new language into the three
OTHER subsystem-integration facets frob.lang._support tracks (T-0405's
FACETS axis): frob.vet._capability_registry.LANGUAGES (dangerous-
operation capability matrix), frob.dup._exhaustiveness.LANGUAGES
(clone-detection rung ladder), and frob.gates._docblocks's fenced-
code-block language buckets (DOC004).

Found post-land: once bash/csharp source files are actually committed
and tracked, `project_lang_conformance_gate` (LANG003) fires because
the auto-generated KNOWN_GAP detail for these three facets
(_capability_status/_dup_status/_docblock_status in
frob.lang._support) names no tracking ticket at all -- unlike
_arch_status, which already cites T-0329 for its own known gap. This
ticket is that missing citation's target, mirroring T-0329's role for
the arch facet.

Required for done: either (a) real subsystem integration for bash and
csharp in all three subsystems, closing the gap for real, or (b) at
minimum, reasoned KNOWN_GAP citations in frob.lang._support's three
status functions naming THIS ticket, so LANG003 stops firing as
"unverified" and starts firing as "tracked, not silent" (the same WARN,
not ERROR, posture every other disclosed gap gets).

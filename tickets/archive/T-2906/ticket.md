---
id: T-2906
title: wire bash+csharp into frob.vet/frob.dup/frob.gates._docblocks (capability/dup/docblock
  facets)
state: done
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
- tests/test_vet.py
- tests/test_dup.py
- src/frob/vet/_capability_registry/_dangerous_ops_bash_csharp.py
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
- op: add
  glob: tests/test_vet.py
  reason: capability scan positive/negative control tests for bash and csharp
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/test_dup.py
  reason: real find_clones reachability tests for bash/csharp
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/vet/_capability_registry/_dangerous_ops_bash_csharp.py
  reason: split out of _dangerous_ops_other.py to stay under LARGE001's 800-line threshold
  actor: logan
  at: '2026-08-25'
evidence:
- tests/test_vet.py::TestCapabilityScan::test_bash_pipe_to_shell_detected
- tests/test_vet.py::TestCapabilityScan::test_bash_eval_detected
- tests/test_vet.py::TestCapabilityScan::test_bash_benign_file_has_no_capabilities
- tests/test_vet.py::TestCapabilityScan::test_csharp_process_start_detected
- tests/test_vet.py::TestCapabilityScan::test_csharp_binary_formatter_deserialize_detected
- tests/test_vet.py::TestCapabilityScan::test_csharp_benign_file_has_no_capabilities
- tests/test_vet.py::TestCapabilityScan::test_language_for_known_and_unknown_extensions
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_bash_and_csharp_are_registered_languages
- tests/test_capability_registry.py::TestMatrixExhaustiveness::test_no_unexcused_empty_cells
- tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_bash_and_csharp_are_registered_languages
- tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_no_unclaimed_cells
- tests/test_dup.py::TestBashCsharpR1Fires::test_r1_fires_on_bash
- tests/test_dup.py::TestBashCsharpR1Fires::test_r1_fires_on_csharp
- tests/test_gates.py::TestDoc004CsharpUsingDrift::test_using_of_tracked_namespace_unanchored_warns
- tests/test_gates.py::TestDoc004CsharpUsingDrift::test_using_of_tracked_namespace_anchored_passes
- tests/test_lang_support.py::TestDeriveLanguageRegistry::test_bash_and_csharp_capability_dup_docblock_are_implemented
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 0163ae2cf554f977b52228639f24159a030e1685
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
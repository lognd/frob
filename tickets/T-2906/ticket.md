---
id: T-2906
title: wire bash+csharp into frob.vet/frob.dup/frob.gates._docblocks (capability/dup/docblock
  facets)
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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

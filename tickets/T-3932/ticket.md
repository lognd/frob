---
id: T-3932
title: 'F-167: mutation-evidence spawns pytest with cargo/gtest/junit/vitest node
  ids (_evidence_test_ids treats any :: id as pytest-shaped)'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_mutation_evidence.py
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
Consumer report F-167: 'the evidence verifier SPAWNS PYTEST FOR CARGO TEST NODE IDS.' Root cause located and confirmed pre-existing (predates T-3847/T-3925 by a wide margin, traced to T-0755/T-0601): src/frob/tickets/_mutation_evidence.py::_evidence_test_ids filters ticket.evidence to 'ids that look like pytest node ids' via a bare '::' in e and not e.startswith('cmd:') check. Every non-pytest node-id shape this repo now collects also uses :: as a separator -- cargo test (module::path::test_name), gtest (rare but possible), junit-style symrefs -- so a mixed-language ticket's cargo/junit/vitest evidence ids pass this filter and get handed straight into check_ticket_mutation_evidence's kill-oracle argv = ('uv', 'run', 'pytest', *test_ids, '-q'), literally invoking pytest with a cargo test id as an argument.

INSTRUMENTED, RULED OUT: T-3925's _other_language_collected_ids union does NOT reach this path (or the _verify_ids_passing bucketing path at all) -- confirmed by direct code read of all 4 _verify_ids_passing call sites (none pass the T-3925 union in) and a live instrumented repro (monkeypatched run_selected recorded only {'rust': (...)}  for a rust-collected cargo id, never routing to python). This bug is unrelated to and predates both T-3847 and T-3925.

FIX SHAPE: _evidence_test_ids needs to recognize which ids are genuinely pytest-shaped, not just '::'-separated -- likely by checking membership against the collected python id set (matches_collected) the same way binding/verification now do, or by using frob.testing.LANGUAGE_COLLECTORS to resolve which language(s) each id actually belongs to before deciding whether pytest is the right kill-oracle for it. A mixed-language ticket may need per-language kill-oracle dispatch (mutate cargo-covered lines and re-run via cargo test, not pytest) -- scope that decision explicitly rather than just filtering non-python ids out silently (which would just make cargo/vitest evidence permanently exempt from the mutation-evidence obligation, a different but real gap).
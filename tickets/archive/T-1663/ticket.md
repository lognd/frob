---
id: T-1663
title: 'Classify every gate rule: semantic, legitimately lexical, or lexical-and-wrong'
state: done
kind: docs
origin: human
created: '2026-08-06'
priority: high
parent: T-1662
tier: ticket
sprint: null
scope:
- docs/**
- src/frob/gates/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
The classification pass that must precede any rewrite, so the epic acts on evidence rather than on the signal-count heuristic that produced its shortlist.

For EVERY rule frob emits (the known-rule registry is the authoritative list -- src/frob/gates/_waive.py's _KNOWN_GATE_RULES plus the registry entries), record:
- what the rule actually asserts, in one line
- what it inspects TODAY: raw text, a regex, an AST node, a resolved symbol, a graph edge
- whether its finding carries a `symref` (the DEAD001/OPAQUE001 hole -- a rule without one turns every waiver into a file-wide amnesty)
- classification: (a) semantic already, (b) lexical but legitimately so, (c) lexical and wrong
- for (b), the REASON it is legitimately textual -- a formatter rewriting comment text, an entropy-based secret scan, a genuinely whole-file rule with no symbol to bind
- for (c), what it should read instead, and which existing substrate provides it

The measured starting shortlist (semantic-signal count vs lexical-signal count across src/frob/gates):
- pure lexical: _refs 22, _tickets_gate 14, _fmt_directives 6, _exclude_hazard 5, _secrets 5, _rule_id_scan 4, _render_lint 3, _mutation_evidence 2, _ffi_boundary 1, _waive_lease 1, _walk_lint 1
- lexical-dominant: _docptr 7/32, _docblocks_refs 4/23, invariants 1/22, _doclink_docanchor 7/14

Treat that shortlist as a HINT, not a verdict -- it counts import-site occurrences, so a gate can score low and still be fully semantic, or score high because it formats text for a message. Read each rule.

Deliverable: a table in docs/ (durable, later children read it), plus one filed ticket per (c) rule. Do NOT fix anything in this ticket; misclassifying a legitimately-textual rule as broken would cost more than the bug it chased.

Known (c) candidates already evidenced, include them and verify:
- REF001 -- "no inbound references" decided by full-path or BARE BASENAME text mention. A file reached via a constructed path or import alias is invisible; a file merely named in prose counts as referenced. Wrong in both directions.
- WALK001 -- unpruned traversal detected by matching `os.walk`/`rglob` call text; an aliased or indirectly-bound traversal evades it.
- The four prose-as-declaration detectors (T-1633, T-1640): they need a shared notion of "this span is explanatory text, not a declaration". The DSL already knows where directive attributes end and free text begins -- reuse that rather than three independent fixes.
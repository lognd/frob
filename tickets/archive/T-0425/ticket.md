---
id: T-0425
title: Split TODO001 into per-failure-mode rule ids (bare-untracked vs dangling-frob:todo-ticket);
  align with frob's own one-id-per-mode convention
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0397
tier: ticket
sprint: null
scope:
- src/frob/gates/
- frob.toml
- docs/modules/gates.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: existing TODO001 edges test must be updated to TODO002 after the rule split,
    or it silently breaks
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_gates.py::TestCoverageGate::test_todo002_unbound_directive
- tests/test_gates.py::TestCoverageGate::test_todo001_bare_comment_in_touched_file
- tests/test_gates.py::TestCoverageGate::test_todo002_edge_to_closed_ticket
designated_repro_test: null
threat: null
component: null
---
User (2026-07-20): is it smart to categorize both failure modes under TODO001? No. TODO001 conflates TWO distinct failure modes: (a) _todo001_bare -- a bare untracked TODO/FIXME comment (work marked, not accounted for at all; fix = file a ticket + convert to frob:todo T-####); (b) _todo001_edges -- a frob:todo bound to a CLOSED/MISSING ticket (work accounted, but the reference is dangling; fix = ticket is closed so remove the TODO/reopen, or the id is wrong so correct it). Different diagnoses, different fixes, yet one rule id -- so you cannot tier their severity independently, cannot frob:waive one without the other, and cannot filter/report them apart. This VIOLATES frobs own one-id-per-failure-mode convention: every other family splits its modes (WAIVE001/WAIVE002, COV001-004, TEST001-010, DUP001/002, PERF001-004). TODO having ONE id for TWO modes is a self-consistency gap -- exactly the "frob does not apply its own standard to itself" class T-0424 (reflexive completeness) should catch.

FIX: split into distinct rule ids -- e.g. TODO001 = bare untracked TODO/FIXME, TODO002 = frob:todo -> non-open/missing ticket (choose numbering; keep TODO001 as the most common/original mode for waiver back-compat, or migrate existing frob:waive TODO001 sites deliberately). Update _KNOWN_GATE_RULES, the waiver machinery, docs/modules/gates.md rule catalog, and any existing frob:waive TODO001 directives in this repo (+ note the per-project migration for sibling repos). COORDINATE with T-0412 (frob:debt<->frob:todo coherence): the debt/todo coherence adds MORE modes (debt-without-todo, debt/todo ticket-mismatch, todo-on-closed-ticket) -- each of THOSE should also be its own rule id, not piled onto a conflated TODO001. Acceptance: each todo/debt failure mode has its own rule id, independently severable/waivable/reportable; the rule catalog documents each; existing waivers migrated; no mode silently shares an id with a semantically-different one. Queued behind T-0343 (gates/__init__.py overlap).
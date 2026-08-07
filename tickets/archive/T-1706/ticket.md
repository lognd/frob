---
id: T-1706
title: 'frob ticket evidence node-id shape validation: investigate the malformed-id
  gap without breaking pytest-form binding'
state: done
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/__init__.py
- src/frob/app/ticket_runner/_verify.py
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets.py
  reason: unit tests for the new 3+-segment malformed evidence-id rejection
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_tickets.py::TestEvidenceValidation::test_validate_evidence_rejects_three_or_more_double_colon_segments
- tests/test_tickets.py::TestEvidenceValidation::test_validate_evidence_accepts_ordinary_two_segment_pytest_form
designated_repro_test: null
threat: null
component: null
---
## Description

Follow-up to T-1670's part 2 ("malformed ids accepted silently"), split
out after investigation found the naive literal reading would be harmful.

T-1670's own text says: "This graph's convention is `path::Class.method`
-- one `::` then a DOTTED class/method. Pytest's own `path::Class::method`
form is accepted by `frob ticket evidence` without complaint... Fix:
validate the node-id shape AT BIND TIME... and reject the pytest
`::`-separated form."

Investigation while implementing T-1670's part 1 found this cannot be
implemented as literally stated without breaking real, tested, documented
behavior:

- `ticket.evidence` entries are resolved against real pytest node ids via
  `frob.tickets._models.matches_collected`, which requires an EXACT string
  match against `collected` -- and `collected` (from `collect_python_tests`/
  `pytest --collect-only`) is always in pytest's native `path::Class::method`
  (double-`::`) form, never dotted. Rejecting that form at bind time would
  make it impossible to bind evidence using a real collected node id copied
  verbatim from `pytest --collect-only` output -- the most natural, lowest-
  error way to get a correct id.
- `frob.tickets.__init__.normalize_evidence_separator` (T-0293) already
  converts a DOTTED `path::Class.method` id INTO the pytest `::` form for
  storage/resolution -- the existing direction is dot-to-`::`, the opposite
  of what T-1670's literal ask would require.
- The CLI path (`_apply_evidence` in `src/frob/app/ticket_runner/_verify.py`)
  already resolves every id against a real collected set
  (`_collect_python_and_rust_ids`) and rejects (`UnknownEvidence`/
  `EvidenceNotPassing`) anything that does not resolve or pass -- so a
  genuinely malformed/typo'd id is already caught at bind time through the
  real CLI, not silently accepted.

What's still plausibly a real, addressable gap:

1. `normalize_evidence_separator`'s early-return (`if "::" in remainder:
   return entry`) passes through UNCHANGED any id with a remainder that
   already contains `::` -- this correctly leaves a legitimate 2-segment
   pytest id (`path::Class::method`) alone, but ALSO passes through
   unchanged a genuinely malformed 3+-segment id (`path::Class::method::
   extra`) with no rejection at the schema-validation layer
   (`validate_evidence`) itself -- it is only caught later, and only if a
   `collected` set happens to be supplied (true for the real CLI path,
   NOT true for a bare library `add_evidence(root, id, ids)` call with no
   collector, which only WARNS "recorded UNRESOLVED").
2. `frob:tests` DIRECTIVE comments (a SEPARATE namespace from
   `ticket.evidence`, playbook section 5) use the dotted `path::Class.method`
   qualname form by this repo's own convention -- DOC007 flags a `frob:tests`
   directive using pytest's own `::`-form target. If an agent habitually
   copies a `ticket.evidence` id (already normalized to `::` form) verbatim
   into a NEW `frob:tests` directive, DOC007 fires. This is a
   directive-authoring UX gap, not a `frob ticket evidence` bind-time bug --
   worth its own investigation into whether `frob ticket evidence` should
   print the frob:tests-directive-form of a newly-bound id as a hint.

## Plan (sketch, for whoever picks this up)

- Investigate (1): add a schema-level check in `validate_evidence` that
  rejects an id whose remainder-after-first-`::` contains MORE than one
  additional `::` (i.e. 3+ total `::`-segments) -- never reject the
  ordinary 1-or-2-`::` pytest shapes, only the genuinely malformed ones.
- Investigate (2) separately: does `frob ticket evidence` need to print a
  "for a frob:tests directive citing this id, use: <dotted form>" hint
  line, to close the copy-paste UX gap without touching `ticket.evidence`'s
  own resolution-critical `::` storage format at all?
- Do NOT implement "reject the pytest `::`-separated form" as literally
  worded in T-1670's original text -- see the investigation above for why
  that breaks the primary, correct way to bind evidence.
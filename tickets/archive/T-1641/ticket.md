---
id: T-1641
title: Burn down gate:DOC warnings (DOC006/DOC011)
state: done
kind: docs
origin: agent
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
- src/frob/gates/_docptr.py
- src/frob/gates/_doclink_docanchor.py
- tests/test_docptr_gate.py
- tests/test_gates.py
- docs/design/cli-regrouping.md
- docs/modules/tickets.md
- docs/modules/gates.md
- docs/modules/vet.md
- docs/audits/README.md
- docs/audits/perf.md
- docs/modules/dup.md
- docs/modules/serve.md
- docs/strata/host.md
- tickets-archive.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: docs/** matched the whole doc tree and its closed-set of doc anchors, pulling
    in ~200 unrelated src symbols into SCOPE002's closure requirement -- narrowed
    to the exact 9 doc files this ticket actually touched
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/design/cli-regrouping.md
  reason: docs/** matched the whole doc tree and its closed-set of doc anchors, pulling
    in ~200 unrelated src symbols into SCOPE002's closure requirement -- narrowed
    to the exact 9 doc files this ticket actually touched
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/tickets.md
  reason: docs/** matched the whole doc tree and its closed-set of doc anchors, pulling
    in ~200 unrelated src symbols into SCOPE002's closure requirement -- narrowed
    to the exact 9 doc files this ticket actually touched
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/gates.md
  reason: docs/** matched the whole doc tree and its closed-set of doc anchors, pulling
    in ~200 unrelated src symbols into SCOPE002's closure requirement -- narrowed
    to the exact 9 doc files this ticket actually touched
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/vet.md
  reason: docs/** matched the whole doc tree and its closed-set of doc anchors, pulling
    in ~200 unrelated src symbols into SCOPE002's closure requirement -- narrowed
    to the exact 9 doc files this ticket actually touched
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/audits/README.md
  reason: docs/** matched the whole doc tree and its closed-set of doc anchors, pulling
    in ~200 unrelated src symbols into SCOPE002's closure requirement -- narrowed
    to the exact 9 doc files this ticket actually touched
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/audits/perf.md
  reason: docs/** matched the whole doc tree and its closed-set of doc anchors, pulling
    in ~200 unrelated src symbols into SCOPE002's closure requirement -- narrowed
    to the exact 9 doc files this ticket actually touched
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/dup.md
  reason: docs/** matched the whole doc tree and its closed-set of doc anchors, pulling
    in ~200 unrelated src symbols into SCOPE002's closure requirement -- narrowed
    to the exact 9 doc files this ticket actually touched
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/serve.md
  reason: docs/** matched the whole doc tree and its closed-set of doc anchors, pulling
    in ~200 unrelated src symbols into SCOPE002's closure requirement -- narrowed
    to the exact 9 doc files this ticket actually touched
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/strata/host.md
  reason: docs/** matched the whole doc tree and its closed-set of doc anchors, pulling
    in ~200 unrelated src symbols into SCOPE002's closure requirement -- narrowed
    to the exact 9 doc files this ticket actually touched
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tickets-archive.md
  reason: T-1262/T-1531's Done reports (edited to fix DOC006/DOC011 stale/orphan citations)
    live in tickets-archive.md, not tickets.md
  actor: logan
  at: '2026-08-06'
evidence:
- tests/test_gates.py::TestDocstatusGate::test_unresolvable_ticket_mention_fires_doc011
- tests/test_gates.py::TestDocstatusGate::test_ticket_mention_inside_line_wrapped_inline_code_does_not_fire_doc011
- tests/test_gates.py::TestDocstatusGate::test_ticket_mention_across_blank_line_still_fires_doc011
- tests/test_docptr_gate.py::TestDoc006Config::test_profile_section_not_flagged
designated_repro_test: null
threat: null
component: null
---
Burn down gate:DOC warnings (DOC006 x44, DOC011 x9 pre-fix mention counts;
112/53 figures cited in the dispatch brief include waived-line mentions).

Classification per rule:
- DOC006 (config-reference kind): rule-level gap. `[profile]`/
  `[profile.profile]` (T-1575, frob.tickets._profile) is a real,
  code-supported frob.toml section this repo's own frob.toml never
  populates -- the exact false-positive class T-1016's
  `_DECLARED_BUT_UNSET_CONFIG_SECTIONS` allowlist already exists for, just
  missing this one entry. Fixed at the rule level (added to the
  allowlist), not per doc site.
- DOC006 (cli-invocation/code-symbol kinds, docs/design/cli-regrouping.md):
  the rule fires correctly against a doc that is DELIBERATELY describing
  not-yet-built candidate CLI verb groups (a design proposal, T-1238) --
  a shape class the rule's WARN-first-turn-on posture already anticipates
  ("if intentionally external/illustrative/future-facing"). Waived
  per-occurrence with that reasoning (29 findings, one doc).
- DOC006 (doc-anchor-link kind, docs/modules/gates.md): a genuine editorial
  defect -- an anchor link got hard-wrapped mid-slug across a line break,
  producing a stray space inside the anchor text that broke resolution.
  Fixed by un-wrapping the line (real content fix, not a waiver).
- DOC006 (file::symbol kind, docs/modules/vet.md): stale doc reference to
  a function renamed in a later ticket (T-1210:
  `_comment_byte_spans` -> `_comment_byte_spans_from_tree`). Fixed by
  updating the doc.
<!-- frob:waive DOC006 reason="self-referential: this line is prose describing the frob.toml.j2 false-positive class this ticket fixed elsewhere, not a genuine reference" -->
- DOC006 (code-symbol kind, docs/modules/tickets.md): `frob.toml.j2` (a
  bare jinja template filename) misread as a dotted code-symbol path
  because it shares the `frob.` project-namespace prefix and the matcher
  has no non-code-extension exclusion. Waived at the one site (real fix
  would need a new matcher-narrowing rule change, judged out of scope for
  a single occurrence).
- DOC006/DOC011 (historical Done-report prose in tickets.md, several
  sites): disclosed-at-the-time future-facing/deleted-artifact references
  (a doc page later folded and deleted, a CLI flag/subcommand disclosed as
  a not-yet-built follow-up). Waived with the historical-record reasoning
  DOC006 already documents as its own intended escape hatch; tickets.md
  already carries this exact waiver precedent from an earlier ticket.
- DOC011 (self-referential rule documentation, docs/modules/gates.md +
  docs/modules/strata.md): a REAL rule-level bug, not a waiver situation --
  `_INLINE_CODE_RE` (`` `[^`\n]+` ``) rejected any inline code span with an
  embedded newline outright, so a backtick span an editor line-wrapped
  left its second physical line un-blanked and exposed to the DOC011 scan
  as ordinary prose. `docs/modules/strata.md`'s illustrative `T-9999`
  example (inside a wrapped inline code span) was misread as an
  unresolvable real ticket citation. Fixed by mirroring the existing
  T-1228 precedent in `_docptr.py::_prose_tokens` -- a single embedded
  newline is ordinary whitespace inside a span (commonmark semantics), a
  blank line (paragraph break) still is not. This is a DOC011 rule bug
  with NO waiver channel at all today (verified: DOC011 has no
  `_nearby_waived`/`frob:waive` support), so the only path to a correct
  reading was the code fix.
- DOC011 (genuinely orphaned `T-draft-<hex>` citations, 5 sites): draft
  ticket ids that were disclosed at filing time but never survived land
  under a traceable real id (renumbering happens at land; a draft that
  gets dropped/superseded leaves no forwarding trail in this ledger
  today). One (docs/strata/host.md) was traceable to its real successor
  (T-0272) via cross-referencing tickets-archive.md and fixed to cite it
  directly. One (docs/modules/serve.md) was traceable to T-1105 the same
  way. The remaining three (docs/audits/perf.md, docs/modules/dup.md,
  docs/audits/README.md) could not be traced to a real id within this
  dispatch's reasonable effort -- their dead citations were replaced with
  an honest "did not survive land, re-file if still open" note rather
  than either a fabricated id or a silent drop.

Follow-up recorded here since no general mechanism exists yet: a draft
ticket that gets dropped/superseded/renumbered away leaves no trace an
agent can follow later. Consider whether `frob ticket` should record a
draft-id -> real-id (or draft-id -> dropped) mapping at land time so this
class of DOC011 orphan becomes mechanically traceable instead of requiring
tickets-archive.md archaeology per citation.
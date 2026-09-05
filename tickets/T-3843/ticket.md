---
id: T-3843
title: 'DOC006 resolves pointers in ticket frontmatter titles where its own waive
  mechanism cannot be applied: sole ubuntu and macOS CI failure'
state: in-progress
kind: bug
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docptr.py
- tests/test_docptr_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_docptr.py
  reason: extend the T-3724 frontmatter-prose blanking helper to cover ticket titles,
    and add must-fire/must-stay-quiet fixtures (T-3843)
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/test_docptr_gate.py
  reason: extend the T-3724 frontmatter-prose blanking helper to cover ticket titles,
    and add must-fire/must-stay-quiet fixtures (T-3843)
  actor: logan
  at: '2026-09-05'
body_changes:
- mode: set
  reason: add DOC006 waive for the illustrative quoted finding, state the (a)/(b)/(c)
    decision and prose-key enumeration per acceptance criteria
  actor: logan
  at: '2026-09-05'
  old_length: 4581
  new_length: 7563
evidence:
- tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo
- tests/test_docptr_gate.py::TestDoc006TitleFieldExclusion::test_single_line_title_not_flagged
- tests/test_docptr_gate.py::TestDoc006TitleFieldExclusion::test_wrapped_title_not_flagged
- tests/test_docptr_gate.py::TestDoc006TitleFieldExclusion::test_open_ticket_body_still_flagged_alongside_title
- tests/test_docptr_gate.py::TestDoc006TitleFieldExclusion::test_body_violation_below_blanked_title_reports_original_line
- tests/test_docptr_gate.py::TestDoc006TitleFieldExclusion::test_docs_prose_pointer_still_flagged
- tests/test_docptr_gate.py::TestBlankTicketReasonFields::test_title_value_blanked_key_kept
- tests/test_docptr_gate.py::TestBlankTicketReasonFields::test_wrapped_title_continuation_blanked_line_count_preserved
- tests/test_docptr_gate.py::TestBlankTicketReasonFields::test_reason_key_blanking_not_regressed_by_title_addition
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DOC006 resolves pointers written in a ticket's YAML FRONTMATTER TITLE, where the
only waive mechanism it offers cannot be applied. The finding is therefore
unwaivable by construction, and one such finding is currently the SOLE failure
on the ubuntu and macOS CI legs.

MEASURED 2026-09-05.

    tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo
        ::test_doc004_doc006_zero_against_live_repo

    AssertionError: unexpected DOC004/DOC006 finding(s): [Violation(
      rule='DOC006', file='tickets/T-3807/ticket.md', line=4,
      message="config reference pointer ... does not resolve --
      <!-- frob:waive DOC006 reason="quoting the measured finding verbatim, not a live pointer" -->
      [check.stack] is not a real frob.toml/pyproject.toml/Cargo.toml
      section/key")]

Line 4 is the wrapped continuation of T-3807's `title:` key. T-3807 is the
FEATURE TICKET PROPOSING that config section, so the pointer cannot be made to
resolve without implementing the feature it requests.

WHY IT IS UNWAIVABLE. DOC006's message says: fix the reference, or waive it "if
intentionally external/illustrative/future-facing". The working waive form in
this repo is an inline HTML comment immediately preceding the citation --
verified against the live precedents in tickets/T-1661, T-2886, T-2962, T-1028.
An HTML comment cannot be placed inside a YAML scalar. A body-level waive was
tried on T-3807 and MEASURED not to suppress the finding (still 1 error after
the append). So for a frontmatter finding there is no correct disposition
available at all.

THE PRECEDENT SAYS THIS IS ALREADY DECIDED. `_blank_ticket_reason_fields` in
src/frob/gates/_docptr.py:159 exists for exactly this reason. Its docstring
(T-3724) states the principle:

    "`frob ticket scope`/`fail`/`ack` write these as free-text accountability
     prose at mutation time ... never doc-pointer prose. A reason mentioning a
     future config key or a file path that does not exist YET must not be
     resolved as a DOC006 pointer."

That is a verbatim description of a feature ticket's title. The helper simply
stops at keys matching `_REASON_KEY_RE` (`^(\s*)(\w*reason):\s?(.*)$`) and never
considers `title`.

WHAT TO DO. Extend the existing helper rather than inventing a mechanism. The
narrow change is to blank the `title` value too, preserving line count and
indentation exactly as the reason-blanking already does (T-3724 was careful
about this so other violations keep correct line numbers -- do not regress it;
note the value WRAPS across lines, so the continuation handling matters here as
much as it does for reasons).

DECIDE AND STATE, do not just implement the narrow version:
  (a) Blank `title` only. Smallest change, fixes the measured case.
  (b) Blank every free-text frontmatter key (title, and any others that are
      human prose rather than structured data). More principled -- the rule is
      "prose written at mutation time is not a doc pointer" -- but requires
      enumerating which keys are prose. Do that enumeration and report it even
      if you choose (a); a reader needs to know what else is exposed.
  (c) Skip ticket frontmatter entirely for pointer resolution. Simplest to
      state, and it gives up checking structured frontmatter keys that SHOULD
      resolve if any exist. Say whether any do.
I lean (b) with the enumeration published, because (a) fixes today's instance
and leaves the next prose key to be discovered the same way -- through a red CI
leg. But make the call yourself and give the reasoning.

DO NOT weaken DOC006 in the ticket BODY. The existing docstring is explicit that
body prose "a human reads and is expected to keep correct" still gets checked,
and that distinction is the whole point. Body pointers must keep firing.

MUST-FIRE FIXTURES:
  - a non-resolving pointer in a ticket BODY is still flagged
  - a non-resolving pointer in ordinary docs/ prose is still flagged
MUST-STAY-QUIET FIXTURES:
  - a config section named in a ticket TITLE that does not exist is not flagged
  - the same, where the title WRAPS across two frontmatter lines (the measured
    case -- the citation is on the continuation line, not the `title:` line)
  - existing reason-key blanking still works (no regression)
LINE-NUMBER FIXTURE:
  - a body violation below a blanked title reports its ORIGINAL line number

ACCEPTANCE
- The (a)/(b)/(c) choice stated with reasoning, and the prose-key enumeration
  reported either way.
- `test_doc004_doc006_zero_against_live_repo` passing against the live repo.
- All fixtures above committed, must-fire ones included -- a pointer gate that
  goes quiet is indistinguishable from one that stopped looking.

DECISION (made 2026-09-05, implementing agent): (b), with the enumeration
below published as the durable output.

Rationale: (a) fixes today's instance and nothing else -- the very failure
mode this ticket exists because of (a red CI leg is how the LAST prose key
was discovered). (c) is worse: it also gives up checking legitimately
resolvable structured frontmatter keys, and none of `Ticket`'s frontmatter
fields hold anything DOC006 could usefully resolve anyway (see enumeration),
so (c) buys nothing (a) does not already buy while being less precise about
WHY the exemption exists. (b) costs one extra alternation in the existing
regex and pays for itself the next time a prose field is added.

ENUMERATION of `Ticket` (src/frob/tickets/_models.py) frontmatter fields,
prose vs. structured, as of this ticket:

  PROSE (free text written by a human/agent at mutation time -- exempted):
    - title                          (T-3843: newly exempted)
    - reason                         (T-3724, via `\w*reason` suffix match)
    - scope_breadth_ack_reason       (T-3724, same suffix match)
    - runs_last_parallel_safe_reason (T-3724, same suffix match)
    - no_scope_declared_reason       (T-3724, same suffix match)
    - anchor_reason                  (T-3724, same suffix match)
    (nested `reason:` keys inside scope_changes/triage_changes/body_changes/
    evidence_changes/etc. audit-trail list entries are ALSO caught by the
    same suffix regex, since it matches the key regardless of indent depth)

  STRUCTURED (ids, enums, dates, bools, commit shas, audit-trail scaffolding
  -- correctly left un-blanked; DOC006 could in principle resolve a pointer
  in one of these, though none currently hold citation-shaped text):
    id, state, kind, origin, created, priority, blocked_by, parent, tier,
    sprint, runs_last, milestone, runs_last_parallel_safe, scope,
    findings, evidence_scope, scope_breadth_ack, no_scope_declared,
    scope_changes/triage_changes/body_changes/lease_force_releases/
    evidence_changes/acceptance_amendments/designated_repro_changes/reviews
    (structural fields of these entries: op, glob, actor, at, from, to,
    commit, verdict, etc. -- only their `reason:` sub-keys are prose),
    evidence, kind_history, designated_repro_test, attachments, acceptance,
    threat, component, labels, anchor, land_commit

  Not exempted and NOT prose in the free-text sense, but freeform strings
  worth naming explicitly since they are not enum-constrained: `component`
  (a short category tag, e.g. "gates") and `labels` (short freeform tags).
  Neither wraps across frontmatter lines in practice and neither is written
  as narrative prose the way `title`/`reason` are, so they are left
  un-blanked; if either is ever observed holding a citation-shaped false
  positive, this same mechanism (add the key to the alternation) is the fix.

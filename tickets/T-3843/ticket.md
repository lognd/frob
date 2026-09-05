---
id: T-3843
title: 'DOC006 resolves pointers in ticket frontmatter titles where its own waive
  mechanism cannot be applied: sole ubuntu and macOS CI failure'
state: queued
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

---
id: T-3285
title: close-time disclosure check false-positives on split done-report.md
state: done
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_reporting.py
- tests/unit/test_reporting_t3285_fenced_subheadings.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_reporting_t3285_fenced_subheadings.py
  reason: regression test for the fence-aware subheading fix
  actor: logan
  at: '2026-08-28'
triage_changes:
- field: priority
  old_value: medium
  new_value: high
  reason: sequencing dependency on T-3272 (ledger v2 as default) plus the pending
    PyPI release turns a repo-local annoyance into a first-hour bug for every new
    user
  actor: logan
  at: '2026-08-28'
body_changes:
- mode: append
  reason: 'record the T-3272 ledger-v2-default sequencing: this bug is confined to
    a minority layout today and reaches every new user the moment v2 becomes the scaffold
    default, so it should land before or with T-3272'
  actor: logan
  at: '2026-08-28'
  old_length: 568
  new_length: 2673
evidence:
- tests/unit/test_reporting_t3285_fenced_subheadings.py::TestSubheadingTitlesOutsideFences::test_hash_line_inside_fence_not_a_subheading
- tests/unit/test_reporting_t3285_fenced_subheadings.py::TestSubheadingTitlesOutsideFences::test_real_subheading_after_a_fence_still_detected
- tests/unit/test_reporting_t3285_fenced_subheadings.py::TestSubheadingTitlesOutsideFences::test_unterminated_trailing_fence_swallows_rest
- tests/unit/test_reporting_t3285_fenced_subheadings.py::TestDisclosureShapedLanguageFencedChanged::test_stat_line_starting_with_hash_inside_changed_block_not_flagged
- tests/unit/test_reporting_t3285_fenced_subheadings.py::TestDisclosureShapedLanguageFencedChanged::test_genuine_subheading_outside_fence_still_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3196's close hit: 'Done report contains disclosure-shaped language (non-standard Done-report subsection (Changed))' even though the rendered/merged body (verified directly via _merge_sibling_done_report + disclosure_shaped_language in a REPL) returns None -- no disclosure. The live close path apparently reads a different body representation than the merge helper. Needs investigation: does close call disclosure_shaped_language on the pre-merge ticket.md body, or is there a double-splice duplicating the done-report.md content under ledger v2's split-file format?

URGENCY CONTEXT ADDED BY THE COORDINATOR 2026-08-28, after this ticket was
filed. Nothing in the diagnosis below changes; what changes is who this reaches.

This bug lives in the close path for LEDGER V2's split `done-report.md` file.
Today that is a minority layout: v2 exists, but every project frob scaffolds
still starts on the v1 single-file ledger, so almost nobody outside this repo
can hit it.

T-3272 IS ABOUT TO MAKE V2 THE DEFAULT FOR NEW REPOS. It is an explicit owner
directive and is in flight now. The moment it lands, every newly scaffolded
project is on the layout this false positive attacks -- and the affected verb
is `frob ticket close`, which is on the critical path of the first real
workflow a new user runs. A first-time user meeting a spurious
disclosure-shaped-language refusal on their first close, with a working
workaround nobody has told them about, is a bad first hour with the tool.

The owner is also preparing frob's first real PyPI release (PyPI is stale at
0.0.9), so this ships to strangers rather than to us.

SEQUENCING: this should land BEFORE or WITH T-3272, not after. If T-3272 lands
first, the window between them is a window where new users hit a bug we already
knew about. Say in your Done report which order actually happened.

KNOWN WORKAROUND, recorded so nobody rediscovers it under pressure: name a real
`Filed:` line rather than `Filed: none`. Series DL used this successfully
several times while landing eleven tickets. It is a workaround, not a fix --
the check should not fire on a Tier-A-generated "### Changed" subheading at
all, and a direct REPL call to the real merge+check functions returns None (no
disclosure), which is the evidence that the check and its own underlying
functions disagree.

DO NOT FIX THIS BY LOOSENING THE DISCLOSURE CHECK GENERALLY. T-1648/T-2718 built
it for a real reason. The defect is that it misreads a structural subheading in
a split file as prose disclosure -- a parsing problem, not a policy problem, and
this repo's standing directive is that checks compare SYMBOLS via the grammar
rather than matching text.
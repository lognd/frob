---
id: T-4176
title: Generalize TEST002's absent-vs-measured-zero fix (T-4138) to TEST001/003/004/009
state: queued
kind: bug
origin: human
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: priority
  old_value: medium
  new_value: high
  reason: one of the four rules it generalises to (TEST004) emits at ERROR severity,
    so the collector-degradation conflation can BLOCK a build there rather than merely
    warn as it did under TEST002 -- the consequence is qualitatively different from
    the medium-priority cleanup this was filed as
  actor: logan
  at: '2026-09-07'
body_changes:
- mode: set
  reason: 'carries forward two facts from T-4138''s implementation that cannot be
    recorded on that ticket now it is done: my filed premise named the wrong mechanism
    (collector degradation, not a missing coverage artifact), and TEST004 emits at
    ERROR severity so the same conflation can block a build rather than merely warn
    -- work it first'
  actor: logan
  at: '2026-09-07'
  old_length: 1575
  new_length: 3866
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-4138 (audit item 4: every consumer of the shared
CollectedTests/_valid_edges/_case_count path for the same conflation).

T-4138 fixed TEST002: a frob:tests edge whose evidence depends entirely
on a native test collector (rust/ts/cpp) that failed this run now reports
UNMEASURED (Severity.UNRESOLVED) via _load_tests's new third return
value, failed_test_languages, instead of a false measured-zero WARN.

The IDENTICAL conflation exists, unfixed, in:
- TEST001's naming-convention (no explicit frob:tests edge) path,
  _inferred_unit_cases -- effective==0 there also fires when the
  record's OWN file's language collector failed, not just when there is
  genuinely no convention-matching test.
- TEST003 (_test003_check_package, integration edges) -- package-level,
  so which language's failure should suppress a given package's finding
  needs more thought than TEST002's per-edge check.
- TEST004 (_test004, e2e edges) -- Severity.ERROR, the most
  consequential instance: a failed collector here BLOCKS frob check,
  not just warns.
- TEST009 (_test009, design-file e2e edges) -- same shape as TEST004,
  scoped to .strata files instead of [[system]] entries.

Extend failed_test_languages threading (already plumbed through
_GateInputs/test_gate) to all four, following T-4138's
_test002_unmeasured precedent (Severity.UNRESOLVED, distinct message,
never a silent pass). TEST004's ERROR severity makes it the highest-value
of the four to land first.

See docs/modules/gates.md#test002-unmeasured-vs-measured-zero-t-4138 for
the full audit writeup.
TWO THINGS FROM T-4138'S IMPLEMENTATION THAT BELONG HERE, recorded on this ticket
rather than on T-4138 because that one is now done and its body must not be
rewritten.

FIRST, T-4138's PREMISE WAS PARTLY WRONG AND THE CORRECTION MATTERS FOR THIS
TICKET'S SCOPE. I filed it as "a missing coverage artifact renders as a measured
zero", following the consumer's own framing. The implementer traced it and found
that TEST002's count path never reads the coverage data at all. The real mechanism
is that the test COLLECTOR degrades on failure: when a native collector errors --
their case was a vitest listing command failing -- the collected node ids come
back silently empty, which is indistinguishable from a symbol that genuinely has
no tests. Python already had dedicated handling for a failed collector; the other
languages did not.

So the CLASS was right (an absent measurement rendered as a measured zero) and the
MECHANISM I named was wrong. Anyone generalising the fix under this ticket should
work from the collector-degradation mechanism, NOT from the coverage-artifact
story, or they will instrument the wrong code path. I took the reporter's framing
at face value instead of tracing which code produces the zero; that is worth
knowing when reading any other ticket I filed from a consumer report today.

SECOND, THE SEVERITY ORDERING HERE IS NOT WHAT THE TICKET TITLE SUGGESTS. Of the
four rules this ticket generalises to, TEST004 emits at ERROR severity while the
others are warnings. So the same conflation that produced a warning storm under
TEST002 can produce a hard FAILURE under TEST004 -- a build stopped because a
collector errored, reported as though the tests do not exist. WORK TEST004 FIRST
and say so in the done report; the ordering is the difference between noisy and
blocking.

ALSO WORTH CARRYING OVER: T-4138's implementer deliberately did NOT split the
remaining two states (a collector that ran and found nothing for this file, versus
one that found too few cases), because the collected-tests structure carries no
per-file join fraction the way the coverage data does. That deferral is honest and
should be preserved unless this ticket adds the missing structure -- do not
"complete" the three-way split by inventing a distinction the data cannot support.

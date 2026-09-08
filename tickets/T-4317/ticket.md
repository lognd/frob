---
id: T-4317
title: Lock-holder diagnostic helpers mix IO, formatting and branching (3 ARCH103)
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/cache.py
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
THREE ARCHITECTURE ERRORS SIT ON THE LOCK-HOLDER DIAGNOSTIC HELPERS ADDED
YESTERDAY, AND THEY ARE FAILING THE UNSCOPED GATE RUN THAT GUARDS THE RELEASE.

WHAT IS MEASURED. The unscoped gate run reports exactly three errors from the
architecture family, all in the graph cache module, all the same rule: each of the
three lock-holder helpers mixes input/output, string formatting, and several
decision points in a single body. The rule is about one function doing three
different kinds of work at once, not about length.

THESE ARE DIAGNOSTIC HELPERS, WHICH RAISES THE STAKES RATHER THAN LOWERING THEM.
Their whole job is to explain who is holding a lock at the moment a build is
stuck -- they run precisely when something has already gone wrong and nobody is in
a position to debug them. This project has repeatedly measured diagnostics that
produced nothing at the moment they were needed. A function that reads process
state, decides what is relevant, and formats a human-facing string in one body is
hard to test, and an untested diagnostic is an intention rather than a
diagnostic.

SEPARATE THE THREE CONCERNS, WHICH IS WHAT THE RULE IS ASKING FOR. Reading process
state is one thing, deciding which holders matter is another, and rendering a
message for a human is a third. Split along those seams so the decision logic can
be exercised against fabricated process state without needing a real stuck lock.
The two platform-specific readers almost certainly differ only in how they obtain
the raw data; if so, the deciding and formatting halves should be shared rather
than duplicated per platform -- check before assuming, and do not create a second
copy of a rule.

DO NOT CLEAR THIS WITH A WAIVER. A waiver here would assert that mixing these
concerns is correct for this code, and the reasoning above says the opposite. If
after reading them you genuinely believe the rule is wrong for this case, argue it
explicitly with what you found rather than defaulting to it.

TAKE THE OPPORTUNITY TO COVER THE BEHAVIOUR, since these helpers were added to
answer a question that had gone unanswered. Once the decision logic is separable,
a test that feeds it a known set of holders and asserts the resulting message is
cheap. Whether you add it is your call, but say what you decided.

VERIFY by running the unscoped gate check and quoting the architecture family's
error count. One error from a separate ticket covering a stranded deferred-work
directive may still be present; that one is not yours.

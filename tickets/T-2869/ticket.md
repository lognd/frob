---
id: T-2869
title: docs/modules/tickets-landing.md has a frob:enumerates anchor with no members=
  attribute
state: done
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/tickets-landing.md
evidence_scope:
- tests/unit/graph/test_dsl_markdown_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'add BUG002 waiver: this is a doc anchor-verb correction filed as kind=bug,
    not a runtime defect with a fail-then-pass repro'
  actor: logan
  at: '2026-08-22'
  old_length: 1382
  new_length: 1684
evidence:
- tests/unit/graph/test_dsl_markdown_waive.py::TestBrokenDirectEdgeVerbIsLoud::test_well_formed_describes_still_parses_cleanly
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while measuring T-2857's positive control (repo-wide malformed-count
before/after a stricter markdown DSL check): `docs/modules/tickets-landing.
md:2189` has

    <!-- frob:enumerates src/frob/tickets/_models.py::Ticket -->

with NO `members="..."` attribute. `frob:enumerates` requires a mandatory
`members="a,b,c"` attribute (`_ENUMERATES_RE` in `src/frob/graph/dsl.py`);
without it the line never matched the strict regex and was previously
(silently, before T-2857) accepted as "handled" purely because the verb
`enumerates` was in `_MD_HANDLED_VERBS`. T-2857 fixed that blanket-accept
bug, which is why this pre-existing defect is now visible for the first
time -- it is not something T-2857's diff introduced.

This is out of `src/frob/graph/dsl.py`'s scope (a docs/modules/*.md content
fix, not a dsl.py behavior change) and needed domain knowledge of what
`Ticket`'s intended enumerated members actually are, which T-2857 did not
have -- so it is filed here rather than guessed at.

Fix: either add the correct `members="..."` attribute (whatever `Ticket`
fields/attributes this anchor was meant to enumerate), or -- more likely,
since `Ticket` is a pydantic model class and not a collection literal --
this should probably be a `frob:describes` anchor instead of `frob:
enumerates`. Read the surrounding "Evidence-only scope (T-1944)" section
context before choosing.

<!-- frob:waive BUG002 reason="doc anchor-verb correction (frob:enumerates -> frob:describes), not a runtime code defect; no fail-at-main/pass-at-fix repro exists because there is no code behavior to reproduce -- cited evidence proves the mechanism this fix relies on, not a fail-then-pass delta" -->
---
id: T-2069
title: PII012 over-matches the bare word 'token' as credentials category-wide
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_pii.py
- src/frob/gates/**pii**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Measured on current main via `uv run frob check --only pii_structural
--json` (T-2032's post-fix PII012 investigation, this ticket filed while
fixing 3 findings on `src/frob/testing/_coverage_refresh.py`).

PII012's keyword-sweep flags any identifier/comment word containing
'token' as category 'credentials', with no distinction between "a
CLI/lexical argv token" (this repo's overwhelmingly common usage: pytest
argv tokens, ticket-parsing tokens, doc-anchor tokens) and an actual
secret/credential token. Repo-wide count at time of filing:

  27 PII012 findings citing 'matches token' (name), across 9 distinct
  files: src/frob/arch/_abstraction.py, src/frob/gates/_docptr.py,
  src/frob/gates/_tickets_gate.py, src/frob/gates/_todo_fmt.py, and
  5 more (full list in the --json dump this ticket cites as evidence
  context -- not re-pasted here to keep this body short).

None of the 3 examined directly (this file, `_tickets_gate.py`,
`_docptr.py`) refer to a credential -- all are lexical/CLI/doc-anchor
tokens. This does not prove all 27 are false positives (not individually
audited here), but the category is clearly over-broad for the bare word
'token' specifically.

Do NOT weaken PII012 globally or add a blanket exemption -- per this
repo's own T-1967 lesson, an exemption matching the normal case disables
the guard. Options worth considering instead: a narrower keyword-vs-value
heuristic (only flag 'token' adjacent to an actual string-literal
assignment, not a bare identifier/comment name), or moving 'token' out of
the 'credentials' category into its own lower-severity or context-gated
category. Left to the assignee to design; this ticket exists to record
the measured breadth so a future waiver-spree isn't mistaken for evidence
of a real defect count.

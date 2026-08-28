---
id: T-2988
title: 'Docstrings: replace the blanket one-line rule with a utility/reuse test and
  per-visibility tiers; move ticket archaeology out of code'
state: in-progress
kind: docs
origin: human
created: '2026-08-26'
priority: high
parent: T-2994
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docstring*.py
- src/frob/gates/__init__.py
- tests/test_docstring*.py
- tests/gates/*docstring*.py
- docs/modules/docstrings.md
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/*.md
  reason: detector for T-2988's utility/reuse purpose test lives in a new docstring-archaeology
    gate; docs standard lives in docs/modules
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_docstring*.py
  reason: detector for T-2988's utility/reuse purpose test lives in a new docstring-archaeology
    gate; docs standard lives in docs/modules
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/__init__.py
  reason: detector for T-2988's utility/reuse purpose test lives in a new docstring-archaeology
    gate; docs standard lives in docs/modules
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/test_docstring*.py
  reason: detector for T-2988's utility/reuse purpose test lives in a new docstring-archaeology
    gate; docs standard lives in docs/modules
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/gates/*docstring*.py
  reason: detector for T-2988's utility/reuse purpose test lives in a new docstring-archaeology
    gate; docs standard lives in docs/modules
  actor: logan
  at: '2026-08-28'
- op: remove
  glob: docs/modules/*.md
  reason: narrow to the doc file that states the new standard plus the gate catalog
    entry
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/modules/docstrings.md
  reason: narrow to the doc file that states the new standard plus the gate catalog
    entry
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/modules/gates.md
  reason: narrow to the doc file that states the new standard plus the gate catalog
    entry
  actor: logan
  at: '2026-08-28'
triage_changes:
- field: parent
  old_value: null
  new_value: T-2994
  reason: 'T-2994 owns the one doctrine: code and docs carry utility, tickets carry
    narrative'
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DECISION (from the project owner, 2026-08-26). This supersedes the blanket
"every public symbol gets a one-line docstring" rule with something more
precise. Recorded here so it is not re-litigated.

The rule is NOT a line budget. It is a purpose test:

1. A docstring exists to illuminate the function's UTILITY. The operative
   question is: would this docstring make it clearer to a reader -- explicitly
   including an LLM -- how and when to REUSE this code? If yes, it earns its
   length. Long docstrings are fine when they are doing that job.
2. Change narrative, justification, and history do NOT belong in the docstring.
   They belong in the ticket. The docstring may carry a ticket REFERENCE; the
   ticket carries the argument.
3. A function simple enough not to need one should not have one. Absence is a
   valid, intentional state, not a gap to be filled.
4. The bar DIFFERS by visibility: public API, module-public, and private are
   three different standards, not one standard applied three times.

MEASURED BASELINE (2026-08-26, AST walk over `git ls-files "src/**/*.py"`):

| tier    | funcs | documented | undocumented | doc lines | avg  | cite a T-id |
|---------|-------|------------|--------------|-----------|------|-------------|
| public  |  1438 |       1304 |          134 |    13,882 | 10.6 |  747 (57%)  |
| private |  5575 |       5467 |          108 |    40,418 |  7.4 | 2829 (52%)  |

Three things this establishes:

- **54% of docstrings cite a ticket id** (3,576 of 6,771). That is the ticket
  bloat, measured. It is not a handful of offenders.
- **There is no tier distinction today.** 98% of private functions are
  documented (5,467 of 5,575), at almost the same rate as public. Point 4 above
  is currently not practised at all.
- **The mass is on private functions**: 40,418 lines versus 13,882 public, 3x
  the volume, on exactly the tier where the bar should be lowest.

WORKED EXAMPLE, opened at random by the owner --
`src/frob/arch/_python.py`, the function returning
`(rel, func_name, param_types, return_type, body_fingerprint)`. Roughly three of
its ~20 lines say what it returns. The remainder is T-0632/T-0370 archaeology:
which prior ad-hoc walk was folded into which shared field, why one piece stayed
on the raw AST, what adding a projection would have duplicated. Every line of
that is real and worth keeping -- and every line of it belongs in T-0632 and
T-0370, not in the function.

WHAT IS WANTED

- A written standard in the docs stating the purpose test and the three
  visibility tiers, replacing the current blanket one-line rule (which is both
  ignored in practice and no longer what the project wants).
- Enforcement, because an unenforced convention will not hold -- this repo's own
  doctrine is that warnings rot and only gates stick. The most defensible
  mechanical signal is the ticket-archaeology one: a docstring carrying
  change-narrative rather than utility. Detecting "is this prose about the code
  or about the code's history" is tractable when the prose cites ticket ids and
  discusses what changed.
- Migration of existing archaeology into the referenced tickets.

CRITICAL CONSTRAINTS

- MOVE, NEVER DELETE. This content is institutional memory, and this drive has
  repeatedly seen agents avoid repeating a landed mistake because a docstring
  recorded it. A migration that loses the narrative is worse than the bloat.
- MIGRATION HAZARD, read before writing anything: most cited tickets are
  ARCHIVED, and `frob ticket body` on a done ticket has previously written to
  the ACTIVE path and produced a DuplicateId that downed every ledger load
  repo-wide. Establish the safe write path for archived tickets FIRST, on one
  ticket, verified, before doing it at scale.
- Do not mass-strip docstrings to hit a number. The purpose test is a judgement,
  and a mechanical pass that removes utility prose along with archaeology fails
  the entire point of this ticket.
- Any detector needs BOTH directions: a must-fire fixture (a docstring that is
  mostly change-narrative) and a must-stay-quiet fixture (a genuinely long
  docstring that is entirely utility -- these exist and must survive untouched).

ACCEPTANCE

- The standard is written down, names the three tiers, and states the reuse
  test. The old blanket rule is removed or rewritten, not left contradicting it.
- A detector enforces the archaeology half, with both fixture directions, and
  its repo-wide finding count is reported before and after.
- A migration path for archived-ticket writes is proven safe on a single ticket
  before any bulk run, and `uv run frob ticket list` exits 0 after every batch.
- Report before/after docstring line totals split by tier, and confirm no
  narrative was deleted rather than relocated.

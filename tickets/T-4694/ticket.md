---
id: T-4694
title: Register 'frob narrative move' as the Tier-A --fix for DOCARCH002 check 2 (ledger
  write inside the fix transaction, archived-path safe, idempotent)
state: done
kind: feature
origin: human
created: '2026-09-19'
priority: medium
blocked_by:
- T-4693
parent: T-4691
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/narrative/_migrate.py
- src/frob/gates/_fix_engine.py
- docs/commands/narrative.md
- tests/narrative
- tests/gates_suite/test_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/gates_suite/test_fix_engine.py
  reason: TIER_A_HANDLERS coverage assertion in this file must include the new DOCARCH002
    entry
  actor: logan
  at: '2026-09-22'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
body_changes:
- mode: append
  reason: 'owner decision: docstring half split to T-4807; record the narrowed scope
    and the generalisation requirement'
  actor: logan
  at: '2026-09-19'
  old_length: 2572
  new_length: 3597
evidence:
- tests/narrative/test_docarch002_fix.py::TestFixDocarch002NarrativeMove::test_positive_control_moves_prose_and_leaves_pointer
- tests/narrative/test_docarch002_fix.py::TestFixDocarch002NarrativeMove::test_second_run_is_idempotent
- tests/narrative/test_docarch002_fix.py::TestFixDocarch002NarrativeMove::test_archived_ticket_writes_archive_path_and_ticket_list_stays_clean
- tests/narrative/test_docarch002_fix.py::TestFixDocarch002NarrativeMove::test_negative_control_directive_citation_is_untouched
- tests/narrative/test_docarch002_fix.py::test_docs_disclose_the_whole_block_move_limitation
designated_repro_test: null
acceptance:
- text: given a fixture with a '# T-1234:' citation and 3 prose lines under it, when
    frob check --fix runs, then the prose is in T-1234's body and the file keeps a
    single-line pointer
  evidence:
  - tests/narrative/test_docarch002_fix.py::TestFixDocarch002NarrativeMove::test_positive_control_moves_prose_and_leaves_pointer
- text: given that same fixture after one --fix, when frob check --fix runs a second
    time, then neither the file nor the ticket body changes (idempotency, T-2994 constraint
    4)
  evidence:
  - tests/narrative/test_docarch002_fix.py::TestFixDocarch002NarrativeMove::test_second_run_is_idempotent
- text: given a fixture citing an ARCHIVED ticket, when --fix runs, then the body
    is appended on the ARCHIVED path and frob ticket list still exits 0 (T-2994 constraint
    3, the DuplicateId hazard)
  evidence:
  - tests/narrative/test_docarch002_fix.py::TestFixDocarch002NarrativeMove::test_archived_ticket_writes_archive_path_and_ticket_list_stays_clean
- text: given a comment block whose citation is a frob:ticket directive, when --fix
    runs, then the block is not touched
  evidence:
  - tests/narrative/test_docarch002_fix.py::TestFixDocarch002NarrativeMove::test_negative_control_directive_citation_is_untouched
- text: given docs/commands/narrative.md, when this lands, then it states that --fix
    moves the WHOLE cited block and cannot make the load-bearing/archaeology split
    (T-2994 constraint 2)
  evidence:
  - tests/narrative/test_docarch002_fix.py::test_docs_disclose_the_whole_block_move_limitation
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-4694
branch: t-4694
---
Split out of T-4693 per the owner's 18:30 directive: "that move is also registered
as a `frob check --fix` Tier-A auto-fix (a separate 1-2 point leaf if the fix
engine work is non-trivial)". It is non-trivial -- the fix engine has its own
scope/sync/text gates (`src/frob/gates/_fix_engine.py`, `_fix_engine_scope.py`,
`_fix_engine_sync.py`, `_fix_engine_text.py`) and a Tier-A registration is a
contract about determinism, not just a callback.

WHAT: register `frob narrative move` as the Tier-A auto-fix for DOCARCH002
check 2 (a `T-####` citation with 2+ comment lines under it), so
`frob check --fix` performs the migration instead of only printing the remedy.

WHY TIER-A IS THE HARD PART, and what the leaf must prove:
- The fix WRITES A TICKET BODY, not just source. That is unlike every other
  Tier-A fix in the engine, which is source-text-only. The ledger write must be
  inside whatever transaction/rollback the engine gives a Tier-A fix, or a
  half-applied fix leaves narrative in neither place -- which violates T-2994's
  first constraint (MOVE, NEVER DELETE) in the worst possible way.
- ARCHIVED-TICKET WRITE HAZARD (T-2994 constraint 3): most cited tickets are
  archived, and `frob ticket body` on a done ticket has previously written the
  ACTIVE path and produced a DuplicateId that downed every ledger load repo-wide.
  Prove the archived-write path on ONE ticket before wiring the batch fix.
  `frob ticket list` must exit 0 after every batch.
- IDEMPOTENCY (T-2994 constraint 4): `--fix` twice must not duplicate the
  narrative into the ticket body. This is the acceptance criterion most likely to
  be silently wrong.
- THE SPLIT IS A JUDGEMENT, NOT A REGEX (T-2994 constraint 2). An unattended
  `--fix` cannot decide which lines are load-bearing. Therefore the Tier-A fix
  moves the WHOLE cited block and leaves the one-line pointer -- and a block that
  should have kept a load-bearing sentence is a human/agent review, not an
  auto-fix. The leaf must state this limitation in docs/commands/narrative.md so
  nobody runs `--fix` repo-wide expecting judgement.

POSITIVE CONTROL: a fixture file with a `# T-1234:` citation followed by 3 prose
lines; `frob check --fix` moves those lines into T-1234's body and leaves a
single-line pointer; running `--fix` a second time changes neither the file nor
the ticket body (idempotency); a fixture citing an ARCHIVED ticket writes to the
archived path and `frob ticket list` still exits 0.

NEGATIVE CONTROL: a block where the citation is a `frob:ticket` directive is not
touched by `--fix` at all.


SCOPE NARROWED 2026-09-19 (owner decision on the docstring half). This leaf is
the COMMENT-RUN half of the Tier-A fix only. The DOCSTRING half -- keep paragraph
1, route the remainder to the cited ticket or to docs/modules/<module>.md with a
`frob:doc` pointer -- is split out as T-4807, blocked by this leaf, because it
adds a second destination type (docs/modules writes, heading creation, pointer
emission, COV/TEST finding invariance) and would have taken this leaf past three
points.

T-4807 REUSES this leaf's machinery rather than building a parallel one: the same
Tier-A registration, the same ledger write inside the fix transaction, the same
idempotency guarantee, the same archived-path DuplicateId precaution. Design those
here so they generalise to a second destination -- a transaction that can only
write ticket bodies will have to be reopened for T-4807.

The owner's framing for both halves: AUTOMATE IT, NO SEPARATE VERB. Neither half
gets a command an agent has to remember; both are `frob check --fix`.
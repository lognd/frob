---
id: T-2047
title: Post-land sweep files UNATTRIBUTED findings as regressions from the landing
  ticket, discarding its own attribution verdict (5 of 6 in T-2038 were pre-existing)
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
## Problem

The deferred post-land sweep (T-1684) computes a symbolic attribution for
every finding it is about to file, using the T-1690 engine, and then files
ALL of them as "new (rule, file) identities from this land" with equal
confidence -- including the ones its own engine explicitly reports as
`UNATTRIBUTED (no batch commit's touched symbols reach this finding);
candidate commits: []`.

A correct signal is computed and discarded. The result is regression tickets
that name a landing ticket as the cause of findings that engine has already
said it cannot connect to that land, sending agents to investigate work they
did not do.

## Measured evidence (2026-08-10)

Two sweep-filed tickets, from two different lands, both this session:

| ticket | identities | UNATTRIBUTED |
|--------|-----------:|-------------:|
| T-2038 (from T-2034's land) | 12 | 4 |
| T-2043 (from T-2023's land) | 6 | 3 |

For T-2038 the coordinator held an INDEPENDENT pre-land floor measurement
(`frob check --json` through `scripts/check_summary.py`, taken shortly before
T-2034 landed). It recorded exactly these six errors:

    F401    tests/test_gates_fmt_directives.py:24
    F401    tests/unit/test_tickets_evidence_only_scope.py:17
    ARCH001 src/frob/app/ticket_runner/_query.py:324
    ARCH103 src/frob/app/ticket_runner/_query.py:324
    ARCH001 src/frob/app/ticket_runner/_rapid_sweep.py:906
    ARCH001 src/frob/app/ticket_runner/_rapid_sweep.py:1500

FIVE of the six identities T-2038 filed as NEW were already present before
the land. Only DRIFT002 was genuinely new -- and DRIFT002 is precisely the
one the attribution engine ATTRIBUTED. The engine got every call right; the
sweep ignored it.

The cause of the false-new set is a stale or empty rolling baseline: whatever
the baseline had not previously recorded looks new. But the attribution
result is an independent signal that already distinguishes the two cases, and
it is being thrown away.

## Why this costs throughput

Each such ticket is dispatched, investigated, and disposed of by an agent who
must re-measure to discover most of it was never real. That happened twice
today. The ticket body's own escape hatch ("if these are pre-existing residue
the rolling baseline had not recorded yet, close with that finding stated
explicitly") puts the burden on a human or agent to falsify a claim the tool
had the evidence to avoid making.

## Proposed fix

Use the attribution result the sweep already computes:

- Findings the engine ATTRIBUTES to the landing commit are filed as now --
  a real regression, named as such.
- Findings the engine reports `UNATTRIBUTED` with empty candidates must NOT
  be presented as caused by this land. Either file them in a clearly separate
  section marked as unattributed-and-possibly-pre-existing, or omit them and
  record the count.

The distinction must be visible in the ticket TITLE and in the identity list,
not buried in an attribution block further down -- the title is what a
dispatcher reads.

## Do NOT fix it this way

- Do NOT suppress UNATTRIBUTED findings entirely and silently. A genuinely
  new finding the engine simply cannot reach (it reports honest
  unattributability, which is its designed behaviour) would then vanish. The
  goal is correct labelling, not fewer findings.
- Do NOT "fix the baseline instead" and leave the reporting as-is. A fresher
  baseline reduces how often this fires but does not stop the sweep from
  asserting causation it cannot support; the two are independent defects and
  this ticket is about the second.
- Do NOT rank findings by heuristics like file path or `git blame`. That is
  unsound attribution and has already produced four wrong answers in this
  session; the whole point is to USE the symbolic engine's verdict rather
  than substitute a guess for it.

## Acceptance criteria

1. A test where the attribution engine returns UNATTRIBUTED for a finding and
   ATTRIBUTED for another, asserting the filed ticket does not present the
   unattributed one as caused by the land. THIS TEST MUST FAIL BEFORE THE
   FIX -- watch it fail and record the observed output.
2. A test that an all-UNATTRIBUTED sweep result does not produce a ticket
   titled as a regression from the landing ticket.
3. Re-run the disposition on T-2038 and T-2043 with the fix in place and
   report what each WOULD have said. Both are still on disk.
4. State whether the rolling baseline being stale/empty is separately worth
   filing, with evidence, or whether fixing the reporting is sufficient. Do
   not file speculatively -- measure first.

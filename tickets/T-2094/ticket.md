---
id: T-2094
title: Over-broad scope is a warning at ticket start, not a refusal, so a ** glob
  silently leases whole subtrees and blocks critical work
state: dropped
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_lifecycle.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given a ticket whose scope matches more files than the TICK009 breadth threshold
    and which has NOT set the acknowledged-broad flag, when frob ticket start runs,
    then it refuses and records no lease, naming the measured file count and the flag
    that would allow it -- this test MUST fail against current main
  evidence: []
- text: given the same ticket WITH the acknowledged-broad flag set, when frob ticket
    start runs, then it succeeds and the broad claim is logged visibly
  evidence: []
- text: given a ticket whose scope is within the threshold, when frob ticket start
    runs, then behaviour is unchanged
  evidence: []
- text: 'CORRECTION TO THIS TICKET EVIDENCE, measured after filing: both cited incidents
    (T-1669 blocking T-2076, T-2079 blocking T-2093) were NOT agents ignoring the
    brief. Both agents DID narrow to named paths as instructed. Their narrowings were
    invisible because a worktree-side scope edit does not reach the lease check, which
    reads mains copy -- captured live: mains tickets/T-2079/ticket.md still listed
    src/frob/tickets/** and src/frob/app/ticket_runner/** while the worktree copy
    listed five named files. That mechanism is now T-2095 (critical) and is the better
    explanation of both blocks. THIS ticket remains valid on its own terms -- an unacknowledged
    broad scope should still be refused at the moment the lease is granted rather
    than merely warned about, and scope_breadth_ack already exists as the opt-in channel
    -- but do NOT justify it with the two blocking incidents, and do NOT assume fixing
    it would have prevented them. It would not have. Acceptance for this ticket is
    unchanged.'
  evidence: []
threat: null
component: ticket_runner
labels:
- fleet-blocking
anchor: false
anchor_reason: null
land_commit: null
---
## Measured evidence: two CRITICAL tickets blocked in one day

1. **T-1669** declared `scope = ['src/frob/tickets/**',
   'src/frob/app/ticket_runner/**', 'docs/design/ledger-v2.md', 'tests/**']`
   -- three subtrees plus all of `tests/**`. T-2076 (critical; the land-time
   verification that fails open under `FROB_AGENT`) was fully implemented,
   evidenced, land-parity clean with a genuine `FAILED_AT_PARENT` repro, and
   was refused with `CrossTicketLeakage`. Its agent correctly recorded
   `frob ticket block T-2076 --by T-1669` and stopped. T-1669 had in fact
   narrowed hours earlier and never needed those paths at all -- but the
   block persisted and the finished ticket sat unlandable.

2. **T-2079** declared `src/frob/tickets/**` and
   `src/frob/app/ticket_runner/**`. T-2093 (critical; a poll loop in
   `refuse_if_land_in_progress` that runs on the LIVE DISPATCH PATH and can
   hang any `frob ticket` verb) could not even `ticket start`: it needs
   `src/frob/tickets/_leases.py` and the call sites in
   `src/frob/app/ticket_runner/__init__.py`. Its agent stopped per the
   playbook rather than forcing. T-2079 was confirmed genuinely active (its
   `frob check --ticket T-2079` running at PID 3612067), so this was a real
   lease, not a stale one.

Both dispatch briefs explicitly instructed named paths over `**` globs, with
the reason given. Both agents used `**` anyway. Per the standing audit rule:
if a written rule was not followed, the rule is not the fix.

Earlier related occurrence, same class: one over-wide scope locked 74 files
at once, and T-1882's repo-wide lease refusal broke every land that filed
residue.

## Root cause, read from source

`_nudge_over_broad_scope` (`src/frob/app/ticket_runner/_lifecycle.py:1029`)
says it outright in its own docstring:

    "Purely a disclosure -- never blocks or exits nonzero; `TICK009`
    itself (a WARN-severity gate finding) is the only thing that actually
    gates anything here, and narrowing scope after seeing this is
    `frob ticket scope <id> --add/--remove`, not something this function
    does for the caller."

So at the exact moment a lease over two entire subtrees is granted, the tool
prints a warning among many other warnings and grants it in full. Scope is
BOTH an evidence-coverage declaration AND a write lease; the lease half
serializes the whole fleet, and nothing refuses it.

## Why the fix is cheap: the opt-in channel already exists

There is already an honest acknowledged-broad channel (WAVE14-B, surfaced in
`src/frob/_cli_parsers/_ticket/_metadata.py:98-108`, "exempts this ticket
from TICK009's scope-breadth nudge"). So a ticket that genuinely needs a
subtree already has a supported way to say so explicitly. Refusing an
UNACKNOWLEDGED broad scope therefore costs legitimate work one flag, not a
redesign -- the same shape as `--allow-cross-ticket`.

## DO NOT FIX IT THIS WAY

- **Do not raise TICK009 to error severity and stop there.** A gate finding
  is evaluated on the next `frob check`; the lease is granted at
  `ticket start`. The refusal has to be at the moment of the claim, or the
  fleet is already blocked by the time anything fires.
- **Do not refuse based on the glob's TEXT** (e.g. "contains `**`"). Refuse
  on the MEASURED breadth -- `large_glob_warnings`/`_tick009_scope_breadth_
  nudges` already compute how many files a scope matches. A narrow `**` in a
  small directory is fine; an enumerated list of 200 files is not.
- **Do not auto-narrow the scope for the author.** Guessing which files a
  ticket will touch, and silently editing its declaration, would break
  evidence coverage (D-02) and could orphan evidence. Refuse and let the
  author choose.
- **Do not exempt tickets whose tier is epic.** An epic holding a subtree
  lease is exactly the leak this repo has already recorded; epics should
  narrow to their own ledger files.
- **Do not make the acknowledged-broad flag silent.** If a ticket claims a
  subtree, that must be visible to the fleet, since it caps parallelism for
  everyone.

## Acceptance direction

The first test must FAIL against current main: `frob ticket start` on a
ticket whose scope matches more than the threshold number of files, without
the acknowledged-broad flag, currently succeeds and records the lease. After
the fix it must refuse, name the measured file count, and name the flag that
would allow it deliberately.

## Drop reason
- 2026-08-11: T-2094's own acceptance criterion [0] says the repro test "MUST fail
against current main". It does not: `_refuse_over_broad_scope_on_start`
(src/frob/app/ticket_runner/_lifecycle.py:928, wired into `start` at
line 692) already promotes TICK009's breadth measure to a hard
`sys.exit(1)` refusal at `frob ticket start`, with `scope_breadth_ack`
as the exact escape hatch T-2094 itself names as "already exists" --
this is T-1866, landed, with its own coverage
(tests/unit/test_app_runners_batch7.py::TestTicketStart.
test_start_refuses_over_broad_scope /
test_start_over_broad_scope_ack_bypasses_refusal, both passing on
main) and doc anchor (docs/modules/tickets.md#mega-glob-scope-refused-
at-start-t-1866).

Verified empirically in this session, not just by reading code: filed
a real ticket with scope='src/frob/gates/**' (75 files, unacked) and
ran `frob ticket start` against it on current main --

  ERROR: ticket start failed: T-2124 scope 'src/frob/gates/**'
    matches 75 files (> 25) -- narrow it to the specific files this
    ticket touches
  ERROR: ticket start failed: T-2124 carries 1 over-broad
    scope entry -- narrow it (...), or if this ticket's honest scope
    really is a package glob (a genuine epic/umbrella), acknowledge it
    explicitly: `frob ticket scope-ack ...`

-- refused, no lease recorded, names the measured count (75 > 25) and
the ack flag, exactly T-2094's acceptance [0]/[1]/[2]. The probe ticket
was dropped immediately after (verification-only, not real work).

T-2094's own standing correction already retracted its original
justification (the T-2076/T-2093 blocking incidents were narrowing-
invisibility, T-2095's subject, not this). The coordinator's later
message (T-2106's 614-collapsed-warnings evidence) is real and valuable
but is about `frob ticket new` accepting an unacknowledged broad scope,
a DIFFERENT enforcement point than this ticket's declared scope
(_lifecycle.py, the `start` path only) and DIFFERENT acceptance
criteria (all three are start-shaped) -- extending the refusal to `new`
is a new, distinct unit of work, not a fold-in achievable inside this
ticket's own acceptance without rewriting it. Dropping this one rather
than reshaping it in place, since its acceptance criteria are already
met verbatim and reshaping them would just be re-filing a different
ticket under the same id.

Filed as a new ticket instead (see Done-report-adjacent citation) for
the `ticket new`-time enforcement gap, scoped to wherever `new_ticket`
lives (src/frob/tickets/_new_renumber.py or its CLI parser) plus a
severity-scales-with-count fix to the collapsed-warning display -- both
out of _lifecycle.py's own scope, so out of this ticket's reach even if
kept open.

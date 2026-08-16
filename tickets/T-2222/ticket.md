---
id: T-2222
title: fleet_status reports a raw lease COUNT with concurrency guidance attached,
  so reclaimable and root-residual leases read as live agents (6 leases = 4 agents)
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- docs/guides/coordinator-scripts.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'The report distinguishes a reclaimable lease from a live one (fails today:
    leases() returns undifferentiated records)'
  evidence: []
- text: The concurrency guidance clause is computed from the LIVE count, not the raw
    file count
  evidence: []
- text: A lease whose worktree IS the repo root is reported as structurally unreclaimable,
    derived from the record's worktree vs resolved root -- never a ticket-id allowlist
  evidence: []
- text: A genuinely live lease MUST STILL report as live (must-still-pass control
    against a fix that marks everything reclaimable)
  evidence: []
- text: 'The report remains strictly read-only: it never releases, modifies, or deletes
    a lease'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
# fleet_status reports a raw lease COUNT and attaches concurrency guidance to it, so reclaimable and permanently-residual leases read as live agents

## Measured evidence (2026-08-16)

`scripts/fleet_status.py` prints, on one line:

    LOAD 13.1  MEM 13.3GB avail  6 lease(s) -- guidance is 3-4 agent concurrent

The count comes from `leases()` (`scripts/fleet_status.py:108`), which globs
`.git/frob-leases/*.json` and returns every record. It performs NO liveness
classification -- there is no `reclaimable`/`stale`/`live` distinction
anywhere in the script.

The guidance clause ("guidance is 3-4 agent concurrent") is attached directly
to that raw number, which makes it a de-facto concurrency governor. Measured
today, of those 6 leases:

- **T-1382** -- `state: queued`, scope `src/frob/**` + `docs/**`, recorded
  2026-08-10 (6 days). `frob worktree release-lease T-1382` reclaimed it
  IMMEDIATELY via `reason=holder-dead`. It was reclaimable the entire time.
- **T-1686** -- recorded against the SHARED ROOT. Liveness is decided by
  `scan_for_live_worktree_process` ("is any process cwd'd into the worktree",
  `_leases.py:1605`); 53 processes were cwd'd into the root at the time of
  measurement, so it reads live permanently. This is **T-2007, already done**,
  whose report states the fix was prevention-only and that "T-1686 itself is
  untouched by this fix". It is accepted permanent residue.

So 6 leases meant 4 live agents. Two of the six could never have been agents.

## Why this is not cosmetic

The coordinator repeatedly held dispatch citing this number while at or below
the actual cap -- directly costing throughput against a 5-min/land target that
was running at ~12 min/land. The number is the input to a throttling decision,
and it silently overstates by the number of dead/residual leases.

This is a recurring defect SHAPE in this repo, not a one-off:
`ps aux | grep -c` counting ~4 lines per land produced a "15-16 concurrent
lands" report when there were 4; a `head -6` truncation of this same lease
list produced a false "an agent abandoned its work" conclusion. Each time, a
summary number included entries that did not mean what the reader assumed.

## Do NOT fix it this way

- **Do NOT fix this in the operator's head.** A memory note ("effective
  concurrency = LEASES minus 1") is exactly the non-fix this repo's standing
  audit duty forbids: it is a rule that must be remembered at the moment of
  reading, which is the moment it has already been forgotten. The report must
  carry the distinction.
- **Do NOT hardcode T-1686 (or any ticket id) as a known-residue exception.**
  An id-keyed exception silently stops being correct the moment that ticket
  closes or another root lease appears. Classify by the RECORD's properties
  (worktree == repo root, ledger state, recorded_at age), not by identity.
- **Do NOT decide liveness by parsing `ps` output or counting processes.**
  That is the precise miscount cited above. Use `/proc/<pid>/cwd` resolution
  (the mechanism `_leases.py` itself uses) or the lease record's own fields.
- **Do NOT infer anything from the lease FILENAME or the worktree path's
  shape.** A series agent works several tickets in ONE worktree, so
  `T-2203`'s lease legitimately pointed at `.claude/worktrees/t2201-series`.
  Read the record's `worktree` field; do not pattern-match the path against
  the ticket id. This is a token/grammar-vs-lexical requirement, not a style
  preference.
- **Do NOT auto-release anything.** This ticket is about REPORTING. A status
  command that mutates lease state is a much larger and riskier change, and
  releasing a live lease is a serious failure.

## Acceptance criteria

1. (MUST FAIL FIRST) A test asserting the report distinguishes a reclaimable
   lease from a live one -- e.g. a fixture with one live lease and one
   holder-dead lease produces a report naming which is which. Fails today:
   `leases()` returns undifferentiated records. Confirm `--check-repro` reads
   FAILED_AT_PARENT before the fix commit.
2. The concurrency guidance clause is computed from the LIVE count, not the
   raw file count. If 6 leases contain 2 non-live, the line must not imply 6
   agents.
3. A lease whose worktree IS the repo root is reported as structurally
   unreclaimable, derived from comparing the record's `worktree` against the
   resolved repo root -- NOT from a ticket-id allowlist.
4. A genuinely live lease MUST STILL be reported as live (must-still-pass
   control). A change that marks everything reclaimable would satisfy 1-3 and
   is catastrophic -- it would invite releasing a live agent's lease.
5. The report does not release, modify, or delete any lease. Read-only.

## Scope note

`scripts/fleet_status.py` is the consumer. If the classification logic
genuinely belongs in `frob.tickets._leases` (which already owns
`lease_staleness_reason` and `scan_for_live_worktree_process`) rather than
being re-implemented in the script, say so and propose that instead -- the
script deliberately stays import-light (see its own comment at :97), so this
is a real design call, not an obvious one. Re-implementing staleness rules in
a second home is the defect shape T-1966 covers; if you must duplicate, say
why explicitly.

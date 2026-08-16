---
id: T-2220
title: A landed ticket does not record its own land commit, so verify_lands.py cannot
  be addressed by ticket id (--plan lands unreachable)
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_models.py
- scripts/verify_lands.py
- docs/guides/coordinator-scripts.md
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: verify_lands.py's frob:doc target -- this ticket changes its argument interface,
    so the doc must move with it
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: the land path gains a persisted land-commit field; the landing module doc
    documents that path
  actor: logan
  at: '2026-08-16'
designated_repro_test: null
acceptance:
- text: Landing a ticket persists the resulting merge_commit as a structured field
    on the ticket record, written by the land path itself
  evidence: []
- text: verify_lands.py accepts a ticket id and resolves via that field, and a SHA
    argument MUST STILL WORK (must-still-pass control)
  evidence: []
- text: A --plan land (no ticket id in the commit subject) is resolvable by ticket
    id -- the case a log grep cannot reach
  evidence: []
- text: A never-landed ticket id is refused distinguishably from a typo'd SHA
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
# A landed ticket does not record its own land commit, so the prescribed verification tool cannot be run from a ticket id

## Measured evidence (2026-08-16)

`scripts/verify_lands.py` is the standing hourly duty for confirming a land.
The things it verifies are identified by TICKET. It accepts SHAs only:

    scripts/verify_lands.py:79   parser.add_argument("shas", nargs="+")

    $ python3 scripts/verify_lands.py T-2211 T-2208
    UNKNOWN-SHA T-2211  (typo? not a commit in this repo)
    UNKNOWN-SHA T-2208  (typo? not a commit in this repo)

Nothing persists the resulting commit per-ticket, so there is no field to
resolve a ticket id against:

    $ git show main:tickets/T-2211/done-report.md | grep -E "[0-9a-f]{12,40}"
    (no output -- no sha anywhere in the done report)

    $ git show main:tickets/T-2211/ticket.md | grep -iE "commit|sha|landed"
    (only prose matches in the body; no structured field)

The land DOES know the value. `merge_commit` is produced at
`src/frob/tickets/_land.py:1383` and appended to `own_commits` at :1384; the
LAND-PROOF path verifies against it. It is computed, used, and then dropped.

## Why this is not cosmetic

The only remaining ticket -> land-commit path is a log grep, which is
ALREADY RECORDED AS BROKEN in this repo's own operating notes:
`git log --grep="land T-####"` misses `--plan` lands entirely, because those
commit as `chore(tickets): land --plan` with no ticket id in the subject.

That miss has already caused real damage once: it led to a correctly-blocked
T-2205 being requeued, and the "repair" that followed wrote a duplicated
`blocked_by: [T-2211, T-2211]`, which is what T-2216 now exists to fix. So
the missing field has already produced one ledger corruption and one
downstream ticket.

The two failure modes compose badly: the verification step that is supposed
to catch a bad land is the same step that cannot be addressed by ticket id.

## Do NOT fix it this way

- **Do NOT make `verify_lands.py` grep the git log for `land <id>`.** That
  reproduces the exact `--plan` blind spot described above, and hides it
  behind a tool that now LOOKS authoritative. A tool that silently reports
  nothing for a whole class of lands is worse than one that refuses the input.
- **Do NOT match the commit subject for the ticket id by substring/regex.**
  Standing user directive: decide from tokens/grammar, never lexical text.
  The commit subject is prose; the ticket id must come from a structured
  field written by the land itself.
- **Do NOT infer the SHA from commit ORDER, timestamps, or "the most recent
  commit touching tickets/<id>/".** Concurrent agents land continuously; this
  repo has already produced one false regression report from exactly that
  reasoning (a before/after `git rev-parse main` attributed another agent's
  land to the wrong ticket).
- **Do NOT write the field from the coordinator or from a script after the
  fact.** It must be written by the land, in the same commit, or it will
  drift from reality the first time a land is retried.

## Acceptance criteria

1. (MUST FAIL FIRST) A test that lands a ticket and asserts the ticket's
   persisted record names the resulting land commit. Against today's tree
   this fails because no such field exists -- confirm `--check-repro` reads
   FAILED_AT_PARENT before the fix commit.
2. The field is written by the land path that produces `merge_commit`
   (`src/frob/tickets/_land.py:1383`), not by a caller, and is a structured
   model field (`src/frob/tickets/_models.py`) -- not prose in a body or
   done-report.
3. `scripts/verify_lands.py` accepts a ticket id and resolves it via that
   field. A SHA argument MUST STILL WORK -- this narrows nothing; include the
   must-still-pass control, since every existing caller passes SHAs.
4. A `--plan` land (subject `chore(tickets): land --plan`, no id in the
   subject) is resolvable by ticket id. This is the case a log grep cannot
   reach, so it is the criterion that discriminates a real fix from the
   forbidden one.
5. An unlanded / never-landed ticket id is REFUSED distinguishably -- it must
   not read as "verified" and must not read the same as a typo'd SHA.

## Scope note

`scripts/verify_lands.py` is in scope as the consumer. The producer side is
the land commit path plus the ticket model. If the implementer finds the
field already exists under another name, STOP and report rather than adding
a second one -- two homes for one fact is the defect shape T-1966 covers.

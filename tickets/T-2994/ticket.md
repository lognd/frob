---
id: T-2994
title: 'Epic: narrative belongs in tickets, code and docs carry utility'
state: queued
kind: docs
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
ONE DOCTRINE, four measured instances. The owner arrived at this incrementally
across a session; this epic records it once so it is not re-litigated per site.

THE RULE: code and docs carry UTILITY -- what this is for, how to use it, what
a reader about to modify or reuse it needs to know. Tickets carry NARRATIVE --
why we arrived here, what a prior attempt got wrong, which policy superseded
which. The artefact may carry a ticket REFERENCE; the ticket carries the story.

Corollaries the owner stated:
- Long prose is fine when it is doing the utility job. This is not a line
  budget.
- The operative test for a docstring: would this make it clearer to a reader,
  explicitly including an LLM, how and when to REUSE this code?
- A thing simple enough to need no prose should have none. Absence is a valid
  intentional state.
- The bar differs by visibility: public API, module-public, and private are
  three standards, not one applied three times.
- For docs specifically: keep the information ABOUT THE CHANGES -- what the
  current behaviour is and what changed. The narrative around it goes to the
  ticket.

MEASURED 2026-08-26 (all figures from AST/paragraph analysis over
`git ls-files`, not estimates):

| instance                              | volume                                  |
|---------------------------------------|-----------------------------------------|
| docs .md paragraphs citing a T-id     | 30,959 lines = 44% of all 69,736 doc lines; 137 of 146 files (94%) |
| docstrings                            | 73,475 lines over 8,044 docstrings, avg 9.1; 54% cite a T-id |
| `# T-####:` narrative comment blocks  | 1,728 blocks / 11,116 lines (src 8,190, tests 1,514, strata 1,412) |
| `frob:waive` reason continuations     | ~5,161 lines; the 5 longest directives in the repo are waivers at 18-20 lines |

Context: `src/` python is 39.8% prose (111,035 of 279,248 lines).
`design/*.strata` is 65% comments (1,851 of 2,842).

CHILDREN
- T-2987 -- waiver-reason bloat, and the directive-prose cap.
- T-2988 -- the docstring standard: utility/reuse test, three visibility tiers,
  replacing the blanket one-line rule that is both ignored and no longer what
  the project wants.
- (child, this epic) T-id narrative comment blocks in code and .strata.
- (child, this epic) docs narrative.

SHARED CONSTRAINTS -- these apply to every child and are the reason none of this
is a mechanical strip:

1. MOVE, NEVER DELETE. This is institutional memory. Multiple agents during this
   drive avoided repeating a landed mistake purely because such a note existed.
   A migration that loses narrative is strictly worse than the bloat it removes.
2. THE SPLIT IS A JUDGEMENT, NOT A REGEX. The `_socketd.py` T-2961 block the
   owner cited contains both kinds in one comment: "a CLASS statement
   referencing a missing base at module scope raises AttributeError at IMPORT
   time, unlike the fcntl pattern used for FUNCTIONS" is load-bearing for
   whoever edits that guard next and must STAY; the T-2918/T-2934/T-2952/T-2953
   cross-references and historical framing MOVE. Any detector or migration must
   respect that both live in one block.
3. ARCHIVED-TICKET WRITE HAZARD. Most cited tickets are archived, and
   `frob ticket body` on a done ticket has previously written to the ACTIVE path
   and produced a DuplicateId that downed every ledger load repo-wide. Prove the
   archived-write path on ONE ticket, verified, before any batch. Run
   `uv run frob ticket list` (must exit 0) after every batch.
4. IDEMPOTENCY. Running a migration twice must not duplicate content into the
   ticket.
5. IT MUST NOT REGROW. The owner flagged the comment-block pattern from an
   IN-FLIGHT agent diff, not from old code -- it is being written right now, at
   agent speed. Every child needs a standing gate, shipped WARN, burned down,
   then promoted to ERROR (the pattern proven on TICK011 under T-2372). A sweep
   without a gate is a temporary cleanup, not a fix.
6. NOT IN `land`. The owner asked whether land could relocate ticket-prefixed
   blocks automatically. It should not: land is already the most contended and
   failure-prone step (in one day it produced a `state=done` with zero code on
   main, tip-drift refusals, DirtyMain deadlocks, a quarantine deadlock needing
   five attempts, and multiple timeouts), and a land that rewrites source means
   the commit that lands is not the diff that was reviewed. Land may CHECK;
   author-invoked migration commands do the rewriting.

ACCEPTANCE FOR THE EPIC
- The standard is written down once, in docs, covering all four instances and
  the visibility tiers -- and the existing blanket one-line docstring rule is
  rewritten rather than left contradicting it.
- Each child lands its own detector with both fixture directions and its own
  before/after measurement.
- No child deletes narrative; each reports relocated-versus-deleted counts.

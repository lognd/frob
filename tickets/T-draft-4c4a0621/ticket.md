---
id: T-draft-4c4a0621
title: 'DECISION: SF-10 -- design/frob.strata is 70% comment prose with 15.4% literal
  duplicate declarations; defaults, or split the monofile?'
state: queued
kind: docs
origin: agent
created: '2026-09-19'
priority: high
parent: T-4667
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: 'Owner records a decision in the body: which of the three options (defaults-and-inheritance
    in the grammar, split the monofile and move rationale to docs/strata/, or split
    first then defaults later), and what it changes. The decision is coordinated with
    T-4598 in the KERNEL DECOUPLING epic, since both attack the same contention on
    this file from opposite directions.'
  evidence: []
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
DECISION TICKET. SF-10 (MEDIUM). Child of story D (T-4667) under epic T-4662.
NOT implementation work. Do not build anything until the owner records a
decision in this body.

EVIDENCE TABLE ROW, VERBATIM FROM scratchpad/STRATA-FRICTION.md:
| SF-10 | design/frob.strata is 70% comment prose, and its declarations are 15% literal duplicates | 2766 lines: 1948 comment lines, 722 non-blank non-comment; 111 duplicate line instances (15.4%); `clearance Internal;` x24, `attr interface=[` x19 | per node | MEDIUM |

FULL EVIDENCE (SF-10 section, verbatim):
design/frob.strata: 2,766 lines total = 1,948 comment lines + 722 non-blank
non-comment lines. Of those 722, 111 ARE LITERAL DUPLICATES of another line
(15.4%): `clearance Internal;` x24, `attr interface=[` x19, `];` x19,
`attr flag=frob_check_exec_kill_switch;` x8, `access "tickets_ledger" mode write;` x5,
`owns "tickets.md" "0644";` x5, `label Internal;` x4, `attr local;` x4.

Header comment block alone runs ~50 lines and contains a paragraph explaining
that a PREVIOUS VERSION OF THE HEADER WAS WRONG. Construct census: 26 nodes,
119 flows, 1 boundary, 36 claims (as reported by the elaborator), 3 `assert`,
33 `assume`, 162 `attr`, 113 `via`, 150 lines carrying a `via`.

A fix would have to change: the grammar (defaults/inheritance so per-node
boilerplate is not restated) and where the rationale lives.

WHY THIS IS NOT MERELY COSMETIC
This file is the single most contended artifact in the repo: 434 commits in 60
days (SF-01), 65 open tickets name it (SF-06), and its whole-file lease
serialises the fleet (T-4598, the KERNEL DECOUPLING epic). Every line of
restated boilerplate is another reason to open the file, and every reason to
open the file is a lease conflict. Size and contention are the same problem here.

OPTIONS THE EVIDENCE SUPPORTS

Option 1 -- defaults and inheritance in the grammar.
Let a registry, a boundary or a node group declare `clearance Internal`,
`label Internal`, `attr local` and a shared `attr interface=[...]` once, with
per-node override. Would have to change: the grammar, the elaborator (defaulting
must be visible in the elaborated model, or a reader can no longer tell what a
node actually claims), and every gate that reads those attrs. Directly removes
the top four duplicate shapes (24 + 19 + 4 + 4 = 51 of the 111). Shares its
machinery with SF-08 option 2, so decide the two together.

Option 2 -- split the monofile; move rationale out of it.
1,948 of 2,766 lines are COMMENT. Move the rationale to docs/strata/ (where
frob:doc edges already point) and split the model per subsystem. Would have to
change: file layout, load_design_ids' multi-file handling (which already exists
-- design/ is loaded as a set), the scope/lease story (this is the direct
mechanical fix for T-4598 and SF-06), and docs. Changes NO grammar. T-3048's
"no monofiles" is the standing anchor for this option.

Option 3 -- both, in that order: split first (no grammar change, unblocks the
fleet now), add defaults later once the grammar rethink settles.

INTERACTION WITH T-4598 / SF-06, which the owner should weigh
T-4598 (KERNEL DECOUPLING) proposes making shared registry files APPEND-SHARED
rather than whole-file leased. Option 2 attacks the same pain by making the file
smaller and more numerous instead. These are complementary, not alternatives,
but if option 2 is chosen the urgency of T-4598's lease work changes -- coordinate
the decision with that epic rather than in isolation.

ACCEPTANCE
Owner records a decision in the body: which option, and what it changes.

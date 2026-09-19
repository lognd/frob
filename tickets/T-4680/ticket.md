---
id: T-4680
title: 'DECISION: SF-10 -- design/frob.strata is 70% comment prose with 15.4% literal
  duplicate declarations; defaults, or split the monofile?'
state: in-progress
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
no_scope_declared: true
no_scope_declared_reason: '2026-09-19: DECISION ticket -- its deliverable is an owner
  decision recorded in the body, which legitimately changes no files'
body_changes:
- mode: append
  reason: '2026-09-19: owner DECISION D-M6 recorded; this decision ticket''s deliverable
    is complete and it closes with no behavior change'
  actor: logan
  at: '2026-09-19'
  old_length: 3559
  new_length: 5945
- mode: append
  reason: 'BUG002 front door (T-2393): 2026-09-19: DECISION ticket whose sole deliverable
    is an owner decision recorded in the body. Owner recorded D-M6 (the monofile is
    split module by module by hand; no split tool). Implementation belongs to the
    module-system story, not here. No code, model or doc file changes under this id.'
  actor: logan
  at: '2026-09-19'
  old_length: 5944
  new_length: 6268
- mode: append
  reason: 'BUG002 front door (T-2393): 2026-09-19: DECISION ticket whose sole deliverable
    is an owner decision recorded in the body. Owner recorded D-M6 (the monofile is
    split module by module by hand; no split tool). Implementation belongs to the
    module-system story, not here. No code, model or doc file changes under this id.'
  actor: logan
  at: '2026-09-19'
  old_length: 6268
  new_length: 6592
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


## DECISION RECORDED -- owner, 2026-09-19 (D-M6)

**Decided: option 2 (split the monofile), with one binding constraint the option
as written did not have -- the split is done MODULE BY MODULE, BY HAND. No split
tool is to be written.**

D-M6, from the owner's module-system decisions. design/frob.strata stops being a
monofile; each module carries its own model. The 1,948 comment lines and the 111
literal duplicate declarations measured in SF-10 are resolved by the split
itself: a module's clearance, label and interface are stated once in that
module's own file, so `clearance Internal;` x24 and `attr interface=[` x19 stop
being restatements and become one statement each, per module.

Explicitly NOT decided and NOT to be built:
- **No split tool.** A mechanical splitter is refused. The split is hand work,
  module by module, because deciding which module owns which node IS the design
  work and a tool would only relocate text without making that judgment. This
  also answers option 3's "split first, defaults later" -- there is no automated
  first pass to run.
- **No grammar defaults/inheritance (option 1).** The module boundary is the
  unit of sharing; a defaults block would be a second, competing mechanism for
  the same thing. Compare D-M8 on T-4677, which refuses templated assumes for
  the same reason: the module is the unit, not a template.

INTERACTION WITH T-4598, now resolved rather than left open: this ticket's body
previously recorded that T-4598 (append-shared registry files) and a split were
"complementary, not alternatives", and asked the owner to coordinate. D-M6
settles it -- the split is the answer to the contention, and per-module files
end the whole-file lease problem structurally, because a module's model is
leased with that module. T-4598 remains the right fix for the registry files
that are NOT split (the KERNEL DECOUPLING epic owns that call).

CONSEQUENCE FOR T-4668, also appended to that ticket: the single ratchet-lock
loader/writer must be designed for PER-MODULE lock files from the start
(design/<module>.via.lock.json), since migration step 7 of the module system
splits the lock per module.

Closing with no behavior change: the deliverable of a DECISION ticket is the
decision, now recorded above. The hand split itself belongs to the module-system
story being filed by the other planner. No files change under this id.

frob:no-behavior-change reason="2026-09-19: DECISION ticket whose sole deliverable is an owner decision recorded in the body. Owner recorded D-M6 (the monofile is split module by module by hand; no split tool). Implementation belongs to the module-system story, not here. No code, model or doc file changes under this id."

frob:no-behavior-change reason="2026-09-19: DECISION ticket whose sole deliverable is an owner decision recorded in the body. Owner recorded D-M6 (the monofile is split module by module by hand; no split tool). Implementation belongs to the module-system story, not here. No code, model or doc file changes under this id."
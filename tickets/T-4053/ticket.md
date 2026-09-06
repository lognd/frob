---
id: T-4053
title: 'F-253: code-kind tickets refuse vitest ids and the help denies the path that
  works, so an agent abandoned a finished ticket'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_verify.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: F-294 shows the evidence rule is a conjunction of ticket kind AND 'Python-coverable
    scope', not kind alone -- which may dissolve the three-way contradiction I filed
    without needing version skew. It also shows an agent NARROWED its declared scope
    to obtain an evidence path, making scope under-declare what the ticket owns
  actor: logan
  at: '2026-09-06'
  old_length: 4199
  new_length: 7064
- mode: set
  reason: found the actual condition at _evidence.py:2163 -- cmd evidence is allowed
    if kind is docs/ux OR the scope has no Python file at all (T-3156, deliberate).
    That makes all three of my 'contradictory' observations consistent with one rule,
    so I am retracting the version-skew hypothesis. The remaining defects are the
    incomplete help text and the scope-shape coupling
  actor: logan
  at: '2026-09-06'
  old_length: 7064
  new_length: 9835
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-253, 2026-09-06. A TS feature ticket has NO first-class
evidence path, and the documentation actively misdirects agents away from the one
that works -- to the point that an agent ABANDONED CORRECT WORK.

THE MEASURED COST FIRST, because it is the strongest part:

  "The T-0089 agent read the help, believed it, and RETURNED THE TICKET
   IN-PROGRESS; the coordinator closed it by hand."

Wrong documentation caused an agent to give up on finished work. Not a wasted
cycle -- an abandoned ticket that a human then had to close manually.

THE THREE-WAY DISAGREEMENT, and this is what makes it dangerous rather than
merely wrong:
  - THE HELP TEXT says `--evidence-cmd` is for "docs-kind tickets only".
  - THE CODE ON MAIN says CMD_EVIDENCE_ALLOWED_KINDS =
    frozenset({TicketKind.DOCS, TicketKind.UX}) (src/frob/tickets/_models.py:201).
    I verified this directly.
  - THE CONSUMER OBSERVES feature-kind tickets binding successfully this way --
    T-0051, T-0052 and T-0089 all did.
Three sources, three answers. T-4000 landed a help-text fix TODAY that made the
text say docs/ux -- which matches the code but may still not match observed
behaviour.

**THE SEQUENCING TRAP -- READ THIS BEFORE FIXING ANYTHING.** If the enforcement
has a hole and someone closes it, TS feature tickets lose their ONLY working
evidence path, because:
  - vitest node ids are refused for code kinds ("code kinds still require pytest
    node ids"), and
  - --evidence-cmd would then be correctly refused for feature kind.
That leaves a genuine no-exit where today there is at least a working accident.
SO: DO NOT TIGHTEN ENFORCEMENT UNTIL VITEST NODE IDS ARE FIRST-CLASS FOR CODE
KINDS. If the hole is real, it is currently load-bearing.

FIRST TASK, cheap and decisive: on CURRENT main, does a feature-kind ticket
actually get refused when binding --evidence-cmd? One command answers it. Until
that is measured, we do not know whether we are looking at an enforcement hole or
at four-findings-worth of version skew (T-4001 already explains F-215, F-216,
F-219 and F-220 that way).

THE UNDERLYING DEFECT is the pytest assumption, now stated as an explicit rule
rather than an accident: "code kinds still require pytest node ids". This is the
SEVENTH confirmed python-default instance, and the first that is deliberate:
  T-3945 kotlin dotted ids mangled; T-3981 a rust id told it does not exist;
  T-3999 close reaching for pytest on rust-only evidence; T-3937/T-3925 binding
  resolving python+rust only; T-4016 the TS walker emitting no symbol for it();
  T-4042 a pytest-shaped validator rejecting deep cargo ids; and this.
The collector already exists (`collect_ts_tests`). The registry already exists
(`LANGUAGE_COLLECTORS`). What is missing is that the code-kind evidence rule was
written when python was the only language and has never been revisited.

RELATED, ALL FILED, AND ALL NEEDED FOR TS EVIDENCE TO ACTUALLY WORK:
  T-4016  the walker emits no symbol for describe()/it()  (the symbol side)
  T-4045  the vitest collect cache is never refreshed      (the collected-id side)
  this    code kinds refuse vitest ids even when collected (the policy side)
Fixing any one alone leaves TS evidence unusable. Whoever takes this should say
which of the three they are closing and which remain.

ALSO NOTED: `EvidenceCmdSilent` correctly rejects `git grep -q` (exit 0, no
output) as proving nothing -- that is the T-1892 behaviour working as intended --
but its message ALSO says "docs-kind tickets only", so a correct refusal is
delivered with an incorrect explanation.

MUST-FIRE FIXTURE: a vitest node id present in .frob/vitest-collect.json binds to
a FEATURE-kind ticket.
MUST-STAY-QUIET: a nonexistent vitest id is still refused.
THIRD FIXTURE: every message naming the allowed kinds agrees with
CMD_EVIDENCE_ALLOWED_KINDS -- asserted against the constant, not hand-copied, so
they cannot drift again.

ACCEPTANCE
- Whether feature-kind --evidence-cmd is genuinely refused on current main,
  measured and stated.
- Vitest node ids first-class for code kinds BEFORE any enforcement tightening.
- All kind-naming messages derived from the constant.
- All three fixtures committed.
## F-294 CORRECTS THIS TICKET'S MODEL: THE RULE KEYS ON SCOPE SHAPE, NOT ONLY KIND

logand.app-v2, 2026-09-06:

  "`--evidence-cmd` REFUSED FOR A FEATURE TICKET WHILE ops/ (.py files) WAS IN
   SCOPE ('Python-coverable scope, cmd evidence only allowed for docs/ux kind'):
   A SCOPE ENTRY THE TICKET NEVER TOUCHED CHANGED THE EVIDENCE RULES; the agent
   had to REMOVE THE ENTRY to bind vitest evidence."

I analysed this ticket as a question about TICKET KIND -- whether
CMD_EVIDENCE_ALLOWED_KINDS = {DOCS, UX} is enforced, and why the consumer saw
feature-kind calls succeed. That model was incomplete. The refusal message names
a SECOND condition: "Python-coverable scope". So the gate is a conjunction of kind
AND the shape of the declared scope, and a ticket's evidence options change
depending on which FILES it declares -- including files it never edits.

THAT EXPLAINS THE EARLIER CONTRADICTION on this ticket. I recorded a three-way
disagreement: the help text says docs-only, the code says {DOCS, UX}, and the
consumer observed feature-kind tickets binding successfully. If the enforcement
depends on scope shape as well, then feature tickets with NO Python-coverable
scope may legitimately pass while ones with such scope are refused -- so all three
observations can be true simultaneously and no version skew is required. VERIFY
THIS BEFORE ANYTHING ELSE; it may dissolve the contradiction I filed.

THE PERVERSE OUTCOME IS THE PART TO FIX. To bind vitest evidence for TypeScript
work, the agent REMOVED A LEGITIMATE SCOPE ENTRY. So an evidence rule caused a
ticket to under-declare what it owns -- which then feeds every scope-based check
(SCOPE001/002, COV, the write lease) a false picture. This is the wrong-incentive
class (T-4069) reaching a new surface: the cheapest way to satisfy the evidence
rule DEGRADES THE SCOPE DECLARATION, and scope is load-bearing for half the
system. Add it to that ticket's audit set as a sixth instance.

WHAT THIS CHANGES ABOUT THE FIX. The sequencing trap recorded above still stands
-- do not tighten enforcement before vitest node ids are first-class for code
kinds -- but the target is now clearer: A TICKET'S EVIDENCE OPTIONS SHOULD NOT
DEPEND ON SCOPE ENTRIES IT DOES NOT TOUCH. Whether the rule should look at the
DIFF's languages rather than the SCOPE's languages is the design question; the
diff is what the evidence is about, and it is already computed.

ADDITIONAL ACCEPTANCE
- The "Python-coverable scope" condition located and documented alongside
  CMD_EVIDENCE_ALLOWED_KINDS; the three-way disagreement re-checked against it
  before being treated as version skew.
- Evidence eligibility keyed on what the ticket actually CHANGED, not on
  untouched scope entries -- or an explicit reason why scope is the right input.
- No ticket has to narrow its declared scope to obtain a working evidence path.

## RESOLVED BY MEASUREMENT: THE RULE IS A DISJUNCTION, AND THE CONTRADICTION DISSOLVES

I found the condition. src/frob/tickets/_evidence.py:2155-2172:

    """`Err(EvidenceKindNotAllowed)` unless `kind` is in
    `CMD_EVIDENCE_ALLOWED_KINDS`, OR (T-3156) `scope` has NO PYTHON FILE AT ALL
    (`scope_has_python_surface`) -- a Rust-only or docs/ledger-only ticket of ANY
    KIND structurally has no other legitimate D-02 route..."""

    if kind in CMD_EVIDENCE_ALLOWED_KINDS or not scope_has_python_surface(root, scope):
        return Ok(None)

SO THE RULE IS: cmd evidence is allowed if the kind is docs/ux **OR** the scope
contains no Python file at all. It is a deliberate design (T-3156) with a stated
rationale, not an enforcement hole.

THAT DISSOLVES THE THREE-WAY DISAGREEMENT RECORDED ABOVE, and I am retracting the
version-skew hypothesis I attached to it:
  - The consumer's FEATURE tickets bound cmd evidence successfully because their
    scopes were frontend-only -- NO PYTHON SURFACE, so the second clause applied.
  - The SAME kind of ticket was refused once ops/ (.py files) entered scope,
    because the second clause stopped applying.
  - The help text saying "docs-kind only" is simply INCOMPLETE -- it states the
    first clause and omits the second.
All three observations are consistent with one rule. No stale install is
required, and I should not have reached for T-4001 before finding the code.

WHAT REMAINS A REAL DEFECT, narrowed:
1. THE HELP TEXT IS STILL WRONG. T-4000 corrected it from "docs-kind only" to
   docs/ux, which is closer and still omits the scope clause entirely. A user
   reading it cannot discover the route that actually works for a Rust-only or
   frontend-only ticket. Note the WARNING message at :2165 DOES state the full
   rule ("or a scope with no Python file at all") -- so the failure path is
   accurate and the help path is not, which is the worse way round.
2. THE SCOPE-SHAPE COUPLING IS STILL QUESTIONABLE, and this is the design
   question worth keeping. The rationale is sound for its motivating case (a
   Rust-only ticket has no pytest route), but it keys on the DECLARED SCOPE
   rather than the DIFF -- so adding a file a ticket never edits can remove its
   evidence route, and an agent responded by NARROWING ITS DECLARED SCOPE to get
   the route back. Scope is load-bearing for SCOPE001/002, COV and the write
   lease; an evidence rule should not be able to push it toward under-declaration.
   Consider keying on the diff's languages, which is what the evidence is about
   and is already computed.

THE SEQUENCING TRAP ABOVE IS UNCHANGED AND STILL BINDING: vitest node ids must
become first-class for code kinds before any tightening, or TypeScript tickets
lose their only working route.

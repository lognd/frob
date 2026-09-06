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
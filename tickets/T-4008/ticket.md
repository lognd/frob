---
id: T-4008
title: 'F-221: BUG002/BUG003 scores zero over an empty Python subject set, the skip
  flag does not lift it, and the only remedy was re-kinding the ticket'
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
- src/frob/tickets/_mutation_evidence.py
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
Consumer logand.app-v2 F-221, 2026-09-06:

  "T-0187 (CI YAML, generated docs, a strata test) was refused at land: 'bound
   evidence killed zero mutants of its own diff-touched code' because the
   mutation scorer only mutates Python and the ticket's real subject is workflow
   YAML. `--skip-mutation-evidence` does not lift it. Worked around by re-kinding
   the ticket to feature."

THREE SEPARATE FAILURES STACKED, and the third is the worst.

1. A PYTHON-ONLY SCORER JUDGING A NON-PYTHON TICKET. The mutation scorer mutates
   Python; the ticket's subject was workflow YAML. Zero mutants killed is not a
   finding about the evidence -- it is the arithmetic of an empty subject set.
   THIS IS A SUBJECT-COUNT INSTANCE: a rule reporting a score computed over
   nothing, indistinguishable in output from genuinely weak tests. Cross-
   reference T-3985; a scorer that reported "0 mutants generated" instead of
   "0 mutants killed" would have made this self-evident.

2. THE DOCUMENTED ESCAPE HATCH DOES NOT WORK. They passed
   --skip-mutation-evidence and it "does not lift it". A flag that exists
   precisely to bypass this check, and does not, is a no-exit -- the ninth in
   this queue. VERIFY THIS FIRST: does --skip-mutation-evidence cover BUG002/
   BUG003, or only a different mutation check? Either it is broken or its name
   promises more than it does, and both are defects.

3. THE ONLY WORKING REMEDY WAS TO LIE ABOUT THE TICKET. They re-kinded a bug to
   a feature to get it landed. That is the most damaging outcome in the report:
   the enforcement system taught a careful user that the way past a rule is to
   misdeclare the work. Every downstream consumer of ticket kind -- reporting,
   triage, the bug-repro discipline itself -- is now slightly wrong, permanently,
   and the ledger records a false kind forever. A rule that is routinely dodged
   by re-kinding is worse than no rule, because it corrupts the data other rules
   depend on.

THE FIX, in the consumer's own terms and both halves matter:
  - SKIP when the diff contains no mutable Python. A confirmatory-only check
    over an empty mutable set has nothing to say and must say nothing, not zero.
  - OR score the non-Python tests that DO assert the changed behaviour. The
    ticket had a strata test asserting the YAML; that is real confirmatory
    evidence the scorer cannot see.
The first is the minimum and is shippable alone; the second is the honest
long-term answer and should at least be stated.

THIS IS THE PYTHON-DEFAULT PATTERN AGAIN, now confirmed across five paths:
T-3945 (kotlin ids mangled), T-3981 (rust id told it does not exist), T-3999
(close reaches for pytest on rust-only evidence), T-3937/T-3925 (binding
resolved only python and rust), and now the mutation scorer. Whoever takes this
should look at whether a shared "what languages does this ticket's diff actually
contain" helper exists; five call sites each answering that question separately
is how this keeps recurring.

MUST-FIRE FIXTURE: a bug-kind ticket with mutable Python and genuinely
confirmatory-only tests is still refused.
MUST-STAY-QUIET: a bug-kind ticket whose diff contains NO mutable Python lands
without re-kinding and without the skip flag.
THIRD FIXTURE: --skip-mutation-evidence demonstrably lifts the check it names.

ACCEPTANCE
- Whether --skip-mutation-evidence covers BUG002/BUG003, answered and fixed.
- No-mutable-Python diffs report "no subjects", never a zero score.
- Re-kinding is not required to land a non-Python bug fix.
- All three fixtures committed.
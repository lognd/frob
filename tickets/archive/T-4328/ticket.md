---
id: T-4328
title: Audit the 308 rules a blanket ratchet promoted to error on a zero-findings
  criterion
state: done
kind: bug
origin: human
created: '2026-09-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: BUG002 requires a repro test pair, but this ticket corrects config-table
    severity entries against documentation, not a reproducible code defect
  actor: logan
  at: '2026-09-08'
  old_length: 3183
  new_length: 3573
evidence:
- tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_must_still_pass_this_repos_own_frob_toml
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THREE HUNDRED AND EIGHT RULES WERE PROMOTED TO ERROR SEVERITY IN ONE CHANGE ON THE
CRITERION "CURRENTLY REPORTS ZERO FINDINGS", AND AT LEAST ONE OF THEM WAS PROMOTED
AGAINST ITS OWN DOCUMENTATION AND HAD NO WAIVER PATH WHEN IT LATER FIRED.

WHAT IS MEASURED. A single severity-ratchet change promoted 308 rules to error in
the project configuration. The stated criterion was that each rule reported zero
findings at that moment. That is a statement about the tree on one day, not about
whether a rule is load-bearing enough to block a build.

THE ONE CASE ALREADY PAID FOR. The scope-closure rule was among the 308. Its own
module docstring and the gates documentation describe it explicitly as a nudge
rather than a hard block, WARN-only until a future deliberate, measured promotion
ticket -- following an established precedent in this repository for how a rule
gets promoted. The blanket ratchet promoted it anyway. When it later began firing,
its findings turned out to be synthetic, reported against a ledger path that no
longer exists, with no source line for a waiver directive to bind to. The result
was an error-severity rule that no documented mechanism could clear. Five separate
implementers in one day hit it, spent real time on it, and each wrote an
explanation into a Done report instead of a fix, because writing an excuse was the
only available action. That has since been repaired for that one rule.

THE QUESTION THIS TICKET ANSWERS IS HOW MANY OF THE OTHER 307 ARE IN THE SAME
POSITION, and it is a real question rather than a rhetorical one -- most are
probably fine. Audit them against three properties that the promotion criterion
never checked:
  - Does the rule's own documentation or module docstring state a severity that
    contradicts error? A promotion that overrides a documented intent is the
    signature already seen once.
  - When the rule fires, can it be waived by a documented mechanism? A rule
    emitting synthetic findings with no anchorable source line cannot, and that is
    what made the known case unclearable.
  - Is the rule reporting zero because nothing violates it, or because it cannot
    currently measure anything? A rule that is structurally silent reads identical
    to a rule that is satisfied, and promoting the former to error arms a trap
    that springs the first time it gains the ability to fire.

REPORT BEFORE REPAIRING. Produce the list first and say what each flagged rule's
situation is. Do not mass-demote on the strength of the audit alone -- a wrong
demotion silently removes enforcement, which is worse than the friction being
fixed. Where a rule genuinely should be error, leave it and say so.

THE UNDERLYING LESSON IS WORTH STATING IN WHATEVER YOU CHANGE. "Currently zero
findings" is the wrong promotion criterion. It selects for rules that are quiet,
which includes rules that are quiet because they are broken, unreachable, or
unmeasurable. A rule should be promoted because someone decided it must block, and
verified it can be satisfied and cleared when it fires.

VERIFY that the unscoped gate run still reports zero errors after any change you
make, and quote the summary line. Do not regress it.

frob:waive BUG002 reason="config-table severity demotion, not a code defect: there is no failing/passing test pair that reproduces a wrongly-error-severity rule in frob.toml, the correction is verified by test_gates_table_schema.py::test_must_still_pass_this_repos_own_frob_toml (schema validity) plus the frob check --ticket T-4328 before/after error-count comparison in the Done report"
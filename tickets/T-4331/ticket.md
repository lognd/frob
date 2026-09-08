---
id: T-4331
title: Audit remaining rules from the T-3844 zero-findings severity ratchet
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: medium
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4328 audited the 308 rules T-3844 promoted to error on a
zero-findings-that-day criterion, against three properties: (1) does the
rule's own docstring/docs state a severity that contradicts error, (2) is
it waivable by a documented mechanism when it fires, (3) is zero findings
because nothing violates it or because it structurally cannot measure
anything.

T-4328 checked the full 308-rule list against explicit "advisory/WARN-
only/nudge/never a hard build failure/stays warn" language in the gates
source (git grep -niE across src/frob/gates) and demoted the 11 rules that
directly contradicted their own documented intent: INV004, PORT001-IDENT,
PROTO001, REF001, REG008, REG009, REG010, REG011, SYS107, TEST011,
TICK009. See T-4328's Done report for the citation backing each one.

NOT done by T-4328: a full manual per-rule read of the remaining ~297
promoted rules. The grep-based sweep in T-4328 covers property (1) well
(explicit contradictory language is greppable) but does NOT reliably
cover property (2) (waivability -- requires checking each rule's emitted
Violation for a real, waiver-matchable file/line vs a synthetic one,
the way TICK009 and the original SCOPE002 incident were caught) or
property (3) (structural silence -- requires checking whether each rule's
implementation can currently fire at all, e.g. feature-gated behind
config this repo doesn't set, or import-guarded on an optional
dependency).

Suggested approach for whoever picks this up: for each of the remaining
promoted rules, (a) find every `rule="<ID>"` Violation-construction site
and check whether `line` can be a real, waiver-matchable source line or a
hardcoded 0 against a path that may not exist, and (b) check the
containing function for a config/feature flag that would make it silently
unreachable in this repo's default configuration. Do NOT mass-demote
without per-rule justification -- most of the remaining 297 are
plausibly fine and a wrong demotion silently removes enforcement.
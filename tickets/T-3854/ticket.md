---
id: T-3854
title: '_KNOWN_GATE_RULES is a closed frozenset of frob''s own rule ids: a consumer
  repo cannot register its own rule (apollo T-0023)'
state: queued
kind: bug
origin: human
created: '2026-09-05'
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
Parked in a consumer repo: ../apollo T-0023 (filed 2026-09-03, still queued)
cannot be fixed there, because the registry it needs is in frob.

APOLLO'S SITUATION, in their words: T-0012's shell wiring constructs a TOKENS001
Violation directly in `App._merge_tokens_violation`, per their documented design
-- TOKENS001 is not produced by a rules/_*.py module like their other rule ids,
it is merged by the shell from `tokens.check_tokens`'s drift status. frob's
gate:WIRE flags that construction site because TOKENS001 is not in frob's own
`_KNOWN_GATE_RULES`. They left a `frob:waive WIRE001` on the call site and filed
a ticket they cannot action.

VERIFIED IN FROB, 2026-09-05:

    src/frob/gates/_waive.py:215
        _KNOWN_GATE_RULES = frozenset({
            "COV001", "COV002", ...
        })

    src/frob/gates/_waive.py:1338
        def known_gate_rule_ids() -> frozenset[str]:
            return _KNOWN_GATE_RULES

A hardcoded literal of FROB'S OWN rule ids, returned with no extension point. A
consumer repo that legitimately defines its own rule id has no registration
path at all.

THIS IS THE PORTABILITY CLASS AGAIN. The registry silently assumes frob is the
only producer of gate rules. That is true in frob and false in every consumer
repo that defines rules -- which is a thing frob actively encourages, since
`frob.toml` policy rules and consumer-side gates are a shipped feature. The
existing precedent for this failure shape is the set of detectors that hardcode
`src/frob/` and therefore pass vacuously off-repo.

WHAT TO BUILD. A consumer-declarable rule-id set. The obvious home is
`frob.toml` (a `[gates] known_rules = [...]`, or a pointer to a module the way
`[testing_schema] known_keys` already does -- read that precedent first, it
solves an almost identical problem and its shape should probably be copied
rather than a second mechanism invented).

DECIDE AND STATE:
  - Should a declared consumer rule id be accepted anywhere a frob rule id is,
    or only for WIRE001 construction sites? Accepting everywhere is more
    consistent; it also means a typo'd frob rule id in a consumer waive stops
    being caught. Say which, and if you choose "everywhere", say what still
    catches a typo.
  - Is the declaration validated against anything, or is any string accepted?
    An unvalidated list makes the registry meaningless; requiring the rule to
    actually be emitted somewhere is stricter but may be impossible to check
    statically. Pick one with reasoning.

DO NOT fix this by simply adding TOKENS001 to frob's frozenset. That is
apollo's rule id, not frob's, and hardcoding one consumer's rule into the tool
just moves the problem to the next repo. If a stopgap is wanted, say so
explicitly and file the real fix -- do not let the stopgap BE the fix.

MUST-FIRE FIXTURE:   an UNdeclared, unknown rule id at a Violation construction
                     site is still flagged by WIRE001.
MUST-STAY-QUIET:     a consumer-declared rule id is not flagged.

ACCEPTANCE
- The declaration mechanism mirrors the `[testing_schema] known_keys`
  precedent, or a reasoned argument for why it should not.
- The scope question (everywhere vs WIRE001-only) answered.
- The validation question answered.
- Both fixtures committed.
- ../apollo is READ-ONLY. Do not edit their tree; their waive comes out on
  their side once this lands.

---
id: T-0896
title: dup_gate silently no-ops (log-only) when frob-core native is unavailable despite
  [dup].enforce=true
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing
designated_repro_test: null
threat: null
component: null
---
Found while working T-0786 (gate-by-gate vacuous-satisfaction sweep, round
2).

`dup_gate` (src/frob/gates/__init__.py:8175, DUP001/DUP002) is opt-in via
`[dup].enforce = true` in frob.toml (disclosed, fine) -- but when enforce
IS on and the `frob-core` native extension is unavailable
(`core_available()` returns False), it degrades to:

    _log.warning("dup_gate: frob-core not installed; DUP rules skipped")
    return ()

a bare log warning, not a `Violation` -- so `frob check`'s exit code and
violation list are UNCHANGED whether DUP001/002 genuinely found nothing or
silently could not run at all. This repo's own playbook
(docs/guides/agent-playbook.md section 1) documents exactly this failure
mode as a REAL, recurring one: "Fresh worktrees do not inherit a sibling
worktree's build -- strata_core/frob_core come up missing" (T-0144) --
meaning a repo that has opted into `[dup].enforce=true` and then runs
`frob check` from a worktree where `make core` has not yet run gets zero
DUP001/002 enforcement, with a green gate-summary line and only a WARNING
in the logs (which the playbook's own section 3 names as something never
piped/read live in a normal `frob check` invocation).

This is the same class T-0552/TEST013 already fixed for the coverage
gate's own native-unavailable structural fallback ("make the structural-
fallback credit ... LOUD instead of silent") -- DUP never got the
equivalent treatment.

Fix direction: when `[dup].enforce=true` and `core_available()` is False,
emit a loud WARN (or ERROR)-tier Violation naming the missing native and
the remediation (`make core`), instead of a log-only degrade -- mirroring
TEST013's shape for the coverage gate.
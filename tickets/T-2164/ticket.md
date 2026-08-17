---
id: T-2164
title: frob-suggest nudges but never refuses a linter run whose target is OUTSIDE
  the repo, so linting a copied file silently drops path-keyed config and invents
  findings
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .claude/hooks/frob-suggest.py
- tests/test_hook_frob_suggest.py
- docs/guides/claude-hooks.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_hook_frob_suggest.py
  reason: acceptance evidence lives in this hook's existing test file, not a new one
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/guides/claude-hooks.md
  reason: must update frob-suggest.py's doc anchor for the new escalation behavior
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_hook_frob_suggest.py::test_third_identical_command_is_blocked_again
- tests/test_hook_frob_suggest.py::test_ack_prefixed_third_attempt_is_allowed_through
- tests/test_hook_frob_suggest.py::test_fourth_attempt_needs_the_ack_again
- tests/test_hook_frob_suggest.py::test_second_identical_check_pipeline_is_allowed_through
- tests/test_hook_frob_suggest.py::test_second_identical_fleet_probe_is_allowed_through
designated_repro_test: tests/test_hook_frob_suggest.py::test_third_identical_command_is_blocked_again
acceptance:
- text: 'GENERALISE beyond the lint case: the hook''s block-once-then-allow semantics
    means it never changes behaviour for a caller who is confident and wrong. Measured
    on myself today across three distinct rules -- [raw-linters] (I re-ran ruff on
    a copied file and invented three phantom findings), [handrolled-fleet-probe] (I
    re-ran ps/git probes three separate times when scripts/fleet_status.py already
    reported the answer), and [unscoped-symbol-search]. Each time the exact-rerun
    escape cost real work: a wasted agent dispatch, a false ''orphaned lease'' conclusion
    I nearly acted on, and a wrong ''agent died'' diagnosis that led me to requeue
    a correctly-blocked ticket.'
  evidence:
  - tests/test_hook_frob_suggest.py::test_third_identical_command_is_blocked_again
  - tests/test_hook_frob_suggest.py::test_ack_prefixed_third_attempt_is_allowed_through
  - tests/test_hook_frob_suggest.py::test_fourth_attempt_needs_the_ack_again
- text: 'The concrete recurring damage is that the SUGGESTED tool already had the
    answer. scripts/fleet_status.py''s LEASES section prints each lease''s real worktree
    (I inferred it from the ticket id instead and got a false ABSENT), and --ticket
    prints ''BLOCKED BY (still open): ...'' (I grepped for a land commit instead,
    missed it because --plan lands commit as ''chore(tickets): land --plan'' with
    no ticket id, and concluded the agent had died). Neither was a tooling gap. Do
    NOT fix this by making every rule a hard refusal -- some nudges are genuinely
    advisory and a hard block on a legitimate raw command would be worse. Consider
    escalating on REPEAT: allow the first exact-rerun, refuse or require an explicit
    acknowledgement on the third within a session, so a habit gets interrupted while
    a one-off does not.'
  evidence:
  - tests/test_hook_frob_suggest.py::test_third_identical_command_is_blocked_again
  - tests/test_hook_frob_suggest.py::test_second_identical_check_pipeline_is_allowed_through
  - tests/test_hook_frob_suggest.py::test_second_identical_fleet_probe_is_allowed_through
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: eadd8c7d8675239bb76b0c51ab3a66a1be1d5fb9
---

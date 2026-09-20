---
id: T-0219
title: secrets scan misses adjacent sk-live key and placeholder-phrase fakes
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_secrets.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense placeholder-phrase bypass-fix rationale into T-0219 body
  actor: logan
  at: '2026-09-19'
  old_length: 747
  new_length: 1711
evidence:
- tests/test_secrets_gate.py::TestFindsTokens::test_generic_live_key_adjacent_to_other_content_sec001
- tests/test_secrets_gate.py::TestFakeMarking::test_digit_free_mixed_case_your_token_still_fires
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-private (gap 15): SEC001 flagged a fake Slack token but MISSED the sk-live-... key on the adjacent line (detection gap -- the miss matters more than any false positive), and the fake-marker heuristics missed obvious placeholder phrasing ('real-slack-token-here' contains no recognized fake word). Fix both directions: audit the provider table against the fixture file that produced the miss (why did sk-live- not match -- prefix table or format constraint?), and extend placeholder recognition ('...-here', 'your-', 'insert-', 'changeme') with fixtures. Coordinate with T-0190 (GitHub-unflaggable fixtures) so new fixtures satisfy both constraints.

<!-- narrative-moved:src/frob/security/_redact.py:88:T-0219 -->
: Placeholder PHRASES (as opposed to single words above) -- T-0219: a
: fixture like `xoxb-your-...-here` reads as an obvious template
: to a human but contains none of `_PLACEHOLDER_WORDS`. Matched
: case-insensitively against the token text, same as `_PLACEHOLDER_WORDS`.
:
: BYPASS FIX (T-0219 review round 2): this regex alone is a `.search()`
: substring test -- a real, high-entropy token that merely CONTAINS
: `your-`/`insert-`/`-here` anywhere (e.g. a live key naming a tenant
: "your-company") used to suppress SEC001 unconditionally. It is now only
: ever consulted through `_looks_fake`, gated by EITHER
: `_KNOWN_TEMPLATE_SHAPE_RE` (a whole-token structural anchor) OR
: `_looks_low_entropy` (the phrase must be sitting inside human-written
: template text, not real secret noise). Never call `.search()` on this
: pattern directly to decide fakeness again -- go through `_looks_fake`.
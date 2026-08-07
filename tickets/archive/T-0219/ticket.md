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
scope:
- src/frob/gates/_secrets.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_secrets_gate.py::TestFindsTokens::test_generic_live_key_adjacent_to_other_content_sec001
- tests/test_secrets_gate.py::TestFakeMarking::test_digit_free_mixed_case_your_token_still_fires
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-private (gap 15): SEC001 flagged a fake Slack token but MISSED the sk-live-... key on the adjacent line (detection gap -- the miss matters more than any false positive), and the fake-marker heuristics missed obvious placeholder phrasing ('real-slack-token-here' contains no recognized fake word). Fix both directions: audit the provider table against the fixture file that produced the miss (why did sk-live- not match -- prefix table or format constraint?), and extend placeholder recognition ('...-here', 'your-', 'insert-', 'changeme') with fixtures. Coordinate with T-0190 (GitHub-unflaggable fixtures) so new fixtures satisfy both constraints.
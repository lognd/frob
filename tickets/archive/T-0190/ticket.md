---
id: T-0190
title: secrets-gate fixtures trip GitHub push protection -- main is unpushable
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_secrets_gate.py
- src/frob/gates/_secrets.py
- docs/modules/gates.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_secrets_gate.py::TestGitHubPushProtectionUnflaggable::test_this_file_contains_no_github_flaggable_literal
- tests/test_secrets_gate.py::TestGitHubPushProtectionUnflaggable::test_pattern_source_module_contains_no_github_flaggable_literal
designated_repro_test: null
threat: null
component: null
---
GH013 push protection rejects main: the Stripe fixture at tests/test_secrets_gate.py:49 (landed in 48aeed1, T-0157) is realistic enough for GitHub secret scanning despite T-0157's clearly-fake requirement. Every push of main is blocked until resolved. Fix has two parts: (1) make every fixture structurally un-flaggable by GitHub (pattern-invalid tail: wrong length/charset/checksum for the provider) while still firing frob's own gate -- if frob's format constraint is currently so strict that only GitHub-flaggable strings can fire it, LOOSEN the fixture-facing constraint or add a test-only needle path, disclosed; (2) meta-test: fixtures must not match GitHub's published secret-scanning patterns (encode the Stripe/AWS/GitHub-token formats we know) so a future fixture cannot re-trip push protection. REMEDIATION for the already-flagged blob (coordinator step, not this ticket): after all in-flight branches merge, rewrite the unpushed range to replace the flagged fixture in 48aeed1 itself (remote tip predates it, so no force-push needed), or the user may use the GitHub unblock URL instead. This ticket only makes the CURRENT tree safe and drift-locked.
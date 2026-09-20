---
id: T-0427
title: extend SEC001 pattern table toward full provider-format parity (secrets.yaml
  PROVIDER_TOKEN_FORMATS/DETECT_SECRETS_PLUGINS)
state: done
kind: feature
origin: human
created: '2026-07-20'
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
- tests/test_secrets_gate.py
- docs/guides/extending/secrets-scan-providers.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense basic-auth-URL pattern rationale into T-0427 body
  actor: logan
  at: '2026-09-19'
  old_length: 1219
  new_length: 2401
evidence:
- tests/test_secrets_gate.py::TestProviderParityT0427::test_aws_bedrock_key_flagged_sec001
- tests/test_secrets_gate.py::TestProviderParityT0427::test_discord_bot_token_flagged_sec001
- tests/test_secrets_gate.py::TestProviderParityT0427::test_mongodb_atlas_uri_flagged_sec001
- tests/test_secrets_gate.py::TestProviderParityT0427::test_hashicorp_vault_service_token_flagged_sec001
- tests/test_secrets_gate.py::TestProviderParityT0427::test_hashicorp_vault_batch_token_flagged_sec001
- tests/test_secrets_gate.py::TestProviderParityT0427::test_basic_auth_url_flagged_sec001_warn
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while dispositioning docs/design/registry/secrets.yaml (T-0343 drain batch 1). src/frob/gates/_secrets.py's SEC001/SEC002/SEC003 pattern table covers a genuine subset of docs/design/secrets-pii-corpus.md's A.4 provider-format master list (30 rows) and A.2 detect-secrets plugin catalog (26 rows): Anthropic, Stripe (live/test/restricted/publishable/webhook), OpenAI (legacy+project+generic live), AWS access-key-id, GitHub (PAT+fine-grained), GitLab, Slack, Google/GCP API key, Twilio, SendGrid, Square, Braintree, npm, PyPI, HuggingFace, Plaid, PEM private-key headers, JWT structural heuristic. NOT covered: Azure Storage/AD, GCP service-account JSON structural shape, AWS secret access key (entropy+contextual), AWS Bedrock long-lived key, MongoDB Atlas URI, HashiCorp Vault token, Discord bot token, Basic-auth-in-URL, generic API-key keyword+entropy rule, and several detect-secrets-only plugins (Artifactory, Cloudant, IbmCloudIam, IbmCosHmac, IPPublic, Mailchimp, Cloudant, etc). Extend the pattern table (with fixtures per docs/guides/extending/secrets-scan-providers.md's add-an-entry recipe) toward full parity, or narrow the corpus rows this ticket references if some are judged out of scope on review.

<!-- narrative-moved:src/frob/security/_redact.py:468:T-0427 -->
T-0427 (A.4 "Basic-auth in URL"): generic scheme, colon-slash-slash,
user, colon, password, at-sign, host credential-in-URL shape (detect-
secrets `BasicAuthDetector`). (Written out in prose above, not as one
contiguous example string, so this comment does not self-trip the
very pattern it describes -- see `TestGateIsGreenOnItself` below.)
Deliberately LAST among the URL-shaped patterns (ordering discipline
at top of this table) -- `mongodb-atlas-uri` above is a strict subset
of this shape and must claim its span first, or every Mongo URI would
double-report under both providers.

Host segment requires an embedded dot (`[^\s/@]+\.[^\s/@]+`) rather
than a bare `[^\s/]+` -- T-0427 discovery: the un-anchored version
matched `docs/design/secrets-pii-corpus.md`'s own prose row
documenting this exact provider format (a placeholder literal
ending in the single word "host", no dot), a real false positive on
an existing tracked file rather than a fixture. Requiring a dotted
hostname keeps the pattern honest for real URLs (which always have
one) while no longer tripping on bare descriptive placeholder words.
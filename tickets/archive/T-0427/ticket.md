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
scope:
- src/frob/gates/_secrets.py
- tests/test_secrets_gate.py
- docs/guides/extending/secrets-scan-providers.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
---
found while dispositioning docs/design/registry/secrets.yaml (T-0343 drain batch 1). src/frob/gates/_secrets.py's SEC001/SEC002/SEC003 pattern table covers a genuine subset of docs/design/secrets-pii-corpus.md's A.4 provider-format master list (30 rows) and A.2 detect-secrets plugin catalog (26 rows): Anthropic, Stripe (live/test/restricted/publishable/webhook), OpenAI (legacy+project+generic live), AWS access-key-id, GitHub (PAT+fine-grained), GitLab, Slack, Google/GCP API key, Twilio, SendGrid, Square, Braintree, npm, PyPI, HuggingFace, Plaid, PEM private-key headers, JWT structural heuristic. NOT covered: Azure Storage/AD, GCP service-account JSON structural shape, AWS secret access key (entropy+contextual), AWS Bedrock long-lived key, MongoDB Atlas URI, HashiCorp Vault token, Discord bot token, Basic-auth-in-URL, generic API-key keyword+entropy rule, and several detect-secrets-only plugins (Artifactory, Cloudant, IbmCloudIam, IbmCosHmac, IPPublic, Mailchimp, Cloudant, etc). Extend the pattern table (with fixtures per docs/guides/extending/secrets-scan-providers.md's add-an-entry recipe) toward full parity, or narrow the corpus rows this ticket references if some are judged out of scope on review.
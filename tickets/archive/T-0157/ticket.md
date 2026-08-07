---
id: T-0157
title: 'secrets-scan gate: real-looking API tokens in tracked files fail check unless
  marked fake'
state: done
kind: security
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/check/**
- tests/**
- docs/modules/gates.md
- frob.toml
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_secrets_gate.py::TestRedact::test_never_returns_the_token
- tests/test_secrets_gate.py::TestFindsTokens::test_stripe_live_key_sec003
- tests/test_secrets_gate.py::TestFindsTokens::test_pem_private_key_header_flagged_sec003
- tests/test_secrets_gate.py::TestFindsTokens::test_anthropic_key_flagged_sec001
- tests/test_secrets_gate.py::TestFindsTokens::test_stripe_test_key_is_low_severity_warn
- tests/test_secrets_gate.py::TestFakeMarking::test_placeholder_xxxx_tail_is_not_flagged
- tests/test_secrets_gate.py::TestFakeMarking::test_literal_fake_word_in_token_is_not_flagged
- tests/test_secrets_gate.py::TestFakeMarking::test_fake_marker_same_line
- tests/test_secrets_gate.py::TestFakeMarking::test_frob_secret_fake_marker_on_line_above
- tests/test_secrets_gate.py::TestTrackedEnvFile::test_env_file_sec002
- tests/test_secrets_gate.py::TestTrackedEnvFile::test_env_example_is_not_flagged
- tests/test_secrets_gate.py::TestTrackedEnvFile::test_untracked_env_file_is_never_scanned
- tests/test_secrets_gate.py::TestDriftLock::test_every_provider_has_a_fixture
- tests/test_secrets_gate.py::TestGateIsGreenOnItself::test_secrets_module_source_is_clean
- tests/test_secrets_gate.py::TestGateIsGreenOnItself::test_this_test_file_is_clean
- tests/test_secrets_gate.py::TestGateIsGreenOnItself::test_repo_is_clean
- tests/test_secrets_gate.py::TestTrackedEnvFile::test_tracked_binary_file_is_skipped_not_crashed
- tests/test_secrets_gate.py::TestOverlapClaim::test_embedded_overlapping_match_is_not_double_claimed
- tests/test_secrets_gate.py::TestTrackedFilesGitFailure::test_spawn_error_yields_no_tracked_files
- tests/test_secrets_gate.py::TestTrackedFilesGitFailure::test_nonzero_exit_yields_no_tracked_files
designated_repro_test: null
threat: info-disclosure
component: null
---
New gate family: scan TRACKED files (git ls-files, never untracked/.env -- and a TRACKED .env is itself a critical finding) for real-looking API tokens and credentials; any match fails frob check unless the site is explicitly marked fake. INVESTIGATE FIRST: the existing frob:secret directive in the comment DSL -- build on its semantics (e.g. frob:secret fake annotation) rather than inventing a parallel marker; also honor obvious placeholder shapes (XXXX runs, asterisks, the literal words fake/changeme/example/placeholder inside the token) so docs and tests stay writable. Pattern table, named per provider with SPECIAL ATTENTION to: OpenAI (sk- and sk-proj- prefixed), Anthropic (sk-ant-), Stripe (sk_live_/rk_live_/pk_live_/whsec_ -- pk_test/sk_test count as real-looking too, flag at lower severity), and finance/common services: AWS (AKIA/ASIA access ids + paired 40-char secrets), GitHub (ghp_/gho_/ghs_/ghu_/github_pat_), GitLab (glpat-), Slack (xoxb-/xoxp-/xoxa-/xoxs-), Google (AIza...), Twilio, SendGrid (SG.), Plaid, Square (sq0), PayPal/Braintree, npm (npm_), PyPI (pypi-), HuggingFace (hf_), private-key PEM blocks (BEGIN ... PRIVATE KEY), and JWTs (eyJ header heuristic). Each pattern carries provider name, severity, and a format constraint (length/charset/checksum where the format has one) to cut false positives; generic high-entropy fallback only if it can be made honest (document the false-positive class per T-0151 precedent, or omit with written reasoning). CRITICAL implementation constraints: (1) NEVER echo the full matched token in any output, log, or ticket -- redact to provider + prefix + length; (2) the gate's own tests need realistic-SHAPED tokens: construct them clearly fake (e.g. correct prefix + XXXX/pattern-invalid tail) and/or annotate with frob:secret fake so the gate does not fail its own fixtures (T-0151 self-match lesson -- lock this with an explicit test that the test files themselves pass the gate); (3) wire into frob check as a default-on gate with its own rule ids and a waive path requiring a written reason; (4) run the new gate against the whole current repo and make it green honestly -- if anything real-looking is already tracked, that is a finding to surface loudly in the Done report, not to quietly waive. Drift-lock: a provider listed in the pattern table without a fixture exercising it fails the suite.
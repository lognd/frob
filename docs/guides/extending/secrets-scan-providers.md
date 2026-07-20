# Secrets-scan providers

<!-- frob:describes src/frob/gates/_secrets.py::_SecretPattern -->

## What / where

`src/frob/gates/_secrets.py` (T-0157). **Do not confuse with**
`src/frob/strata/_secrets.py`, an unrelated strata modeling primitive for
`SecretSpec`/boundary elaboration in design files -- different module,
different purpose, same word.

Core symbols: `_SecretPattern` (frozen: `provider`, match spec, `label`
severity), built via the `_pat(provider=..., ...)` helper into the
module-level `_PATTERNS` list. `CRITICAL_PROVIDERS` and `ALL_PROVIDERS:
frozenset[str]` are both derived from `_PATTERNS`. `ALL_PROVIDERS` is
explicitly marked in a source comment as the **drift-lock source of
truth**, referencing `tests/test_secrets_gate.py::TestDriftLock.test_
every_provider_has_a_fixture` by name -- one of the few drift-locks in
this codebase that names its own enforcing test in a comment.

Providers covered at time of writing (per the module docstring's "per-
provider mandate," T-0157, extended toward provider-format parity by
T-0427): Anthropic, OpenAI, Stripe (live+test, secret+restricted+
publishable+webhook), AWS access key ids, AWS Bedrock long-lived API keys,
GitHub (PAT + fine-grained), GitLab, Slack, Google, Twilio, SendGrid,
Square, Braintree, npm, PyPI, HuggingFace, Discord bot tokens, MongoDB
Atlas connection URIs, HashiCorp Vault service/batch tokens, generic
basic-auth-in-URL credentials, Plaid (context-gated), PEM private-key
headers, and a JWT structural heuristic -- see `_PATTERNS` in the source
for the full, current, authoritative list; this page names highlights, not
a duplicate enumeration to keep in sync by hand.

Deliberately NOT patterned, and not planned without a dedicated ticket
revisiting the entropy-fallback decision (`_secrets.py`'s module
docstring, "Deliberately OMITTED" section): AWS secret access keys, Azure
Storage Account keys, Azure AD/Entra client secrets, and the generic
keyword+entropy "API key" rule -- none has a fixed, matchable prefix, so a
pattern for any of them degenerates into exactly the noisy entropy
fallback this scanner declines to ship. GCP service-account JSON keys are
also not separately patterned: the PEM `private_key` field embedded in
that JSON already trips `private-key-pem`, so a dedicated whole-document
pattern would be redundant.

## Add-an-entry recipe

1. Add a `_pat(provider=<name>, label="critical"|..., ...)` call to the
   `_PATTERNS` list, with a real (or realistic-shaped) match pattern.
2. **Add a corresponding fixture** in `tests/test_secrets_gate.py` -- a
   literal that should trip the new pattern. `test_every_provider_has_a_
   fixture` fails if a provider in `ALL_PROVIDERS` has no fixture proving
   the pattern actually matches something.
3. If the provider issues fake/test-mode tokens that should not trip the
   scanner in fixtures or docs, confirm `_looks_fake`/`_line_marks_fake`
   cover the new pattern's fake-token shape.

## Drift-locks that fire

- `tests/test_secrets_gate.py::TestDriftLock.test_every_provider_has_a_
  fixture` -- named explicitly in a source comment on `ALL_PROVIDERS`.
- ENV002 (`_env002_violation`/`_is_env_file`) -- separate rule governing
  `.env` file exemption logic, not provider-specific.

## Worked example diff

```python
# src/frob/gates/_secrets.py, in _PATTERNS:
_pat(
    provider="github",
    label="critical",
    prefix="ghp_",
    pattern=r"ghp_[A-Za-z0-9]{36}",
),
```

```python
# tests/test_secrets_gate.py, a new fixture:
def test_github_token_flagged(self) -> None:
    text = "token = 'ghp_" + "a" * 36 + "'"
    violations = _scan_text("example.py", text)
    assert any(v.rule.startswith("SEC") for v in violations)
```

## Common mistakes

- **Source-only edits.** Adding a `_pat` entry without the matching test
  fixture passes locally (the scanner works) but fails the named
  drift-lock test -- this is the one registry in this series where the
  test/source coupling is self-documenting in a comment; do not skip the
  test half thinking the drift-lock is optional.
- **Conflating `gates/_secrets.py` with `strata/_secrets.py`.** They are
  unrelated modules that happen to share a name stem; grep the full path
  before editing.
- **A structural/URL-shaped pattern (no fixed provider prefix) matching
  its own describing prose.** T-0427: an un-anchored `basic-auth-url`
  pattern (`scheme://user:pass@host`) matched the literal placeholder text
  in this codebase's own `docs/design/secrets-pii-corpus.md` row
  describing that exact format -- a real false positive on an existing
  tracked file, not a fixture. Run `TestGateIsGreenOnItself::
  test_repo_is_clean` against a NEW structural pattern before considering
  it done; if it fires on real repo content, tighten the pattern (e.g.
  requiring a dotted hostname) rather than marking the hit `frob:secret-
  fake` by hand -- a hand-marked false positive just moves the same bug to
  the next tracked file that happens to match.
- **Two patterns matching the same shape without ordering.** A new
  structural pattern that is a strict superset of an existing one (e.g.
  `basic-auth-url` vs. `mongodb-atlas-uri`, both `scheme://user:pass@host`
  shapes) must be added AFTER the more specific pattern in `_PATTERNS`
  (this table's documented most-specific-first ordering discipline) or
  every hit under the specific provider double-reports under the generic
  one too.

## See also

- [PII categories](pii-categories.md) -- a related but distinct
  data-sensitivity concern (modeled PII vs. scanned literal secrets).

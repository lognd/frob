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
provider mandate," T-0157): Anthropic, OpenAI, Stripe (live+test,
secret+publishable).

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

## See also

- [PII categories](pii-categories.md) -- a related but distinct
  data-sensitivity concern (modeled PII vs. scanned literal secrets).

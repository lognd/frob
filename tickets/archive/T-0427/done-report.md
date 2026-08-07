## Done report

Extend SEC001 pattern table toward provider-format parity: 8 patterns / 7 providers (aws-bedrock, discord-bot, mongodb-atlas, hashicorp-vault service+batch, basic-auth-url with dotted-host FP fix), per-provider fire tests, honest deliberately-omitted docs. Reviewer APPROVED.

### Changed
```
 docs/guides/extending/secrets-scan-providers.md |  41 ++++++++-
 src/frob/gates/_secrets.py                      | 117 ++++++++++++++++++++++--
 tests/test_secrets_gate.py                      |  97 ++++++++++++++++++++
 3 files changed, 246 insertions(+), 9 deletions(-)
```

### Evidence
(no evidence recorded)

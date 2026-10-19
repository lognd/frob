# Effective policy snapshot

Implements the GATE001 inputs of security.md section 2.7 in
`gob_trust::policy`.

- `PolicySnapshot::from_toml` flattens the policy tables of the config at a
  ref (packs and paths, rules, severities, disabled rules, `fail_on*`,
  `[compute]`, excludes, grants, `replaces`, trust, adapters) into
  canonical dotted keys. Other settings are ignored.
- `PolicySnapshot::with_declaration` adds repository-adapter NotApplicable
  claims and in-source declarations a P+ verdict depends on.
- `PolicySnapshot::diff` yields a `PolicyDelta` listing every added,
  removed or changed setting with old and new value, sorted by key. The
  delta is empty when policy is identical.

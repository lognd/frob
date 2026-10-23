# Effective policy snapshot

Status: current
Owner: gob
Decisions: none

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

## GATE001 classification (`gob_check::gate001`)

`gate001::weakenings` classifies each `PolicyChange` and
`gate001::gate001_findings` emits one Error finding per weakening, with the
message `policy weakened: KEY changed from OLD to NEW`. Strengthening is
silent. Keys named in the `cleared` set (an exception with a ticket or a
reviewer label) are skipped.

- Severities (`rules.*.severity`, `severity.*`): weaker when the rank drops
  (error > warn > advisory > off).
- Disabled rules (`rules.*.disabled`, `disable.*`): weaker when newly disabled.
- `fail_on*`: weaker when the threshold moves to a less strict level.
- Excludes, grants, `replaces`, adapters and declarations: weaker when an
  item is added or the setting is new; removal is silent.
- Packs, trust, `[compute]` and anything else: weaker when removed or changed.

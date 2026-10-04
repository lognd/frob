+++
id = "01M2VFD1JRS4WQNT3DRA7MFAJM"
title = "Nine ticket field-setters become one: frob ticket set field value (priority kind component label tier milestone sprint accept body)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-19T00:00:00Z"
updated = "2026-09-19T00:00:02Z"
aliases = ["T-4696"]
labels = ["cli-debloat", "points-2", "milestone:0.533.0", "component:cli"]
scope = ["src/frob/_cli_parsers/_ticket/__init__.py", "src/frob/_cli_parsers/_ticket/_metadata.py", "src/frob/app/ticket_runner/__init__.py", "src/frob/app/ticket_runner/_lifecycle.py", "tests/unit/test_ticket_set.py", "src/frob/app/_config_external.py", "src/frob/app/ticket_runner/_ledger_mirror.py", "src/frob/strata/_assume_template.py", "docs/modules/vet.md", "src/frob/tickets/_leases.py", "design/frob.strata", "docs/design/registry/capability-via-ratchet.lock.json"]

[[links]]
kind = "blocked-by"
target = "01M2VFD1JJD17QEF1ZFXA7C3R1"

[[acceptance]]
text = "Given a fixture ledger, when frob ticket set priority high runs on a ticket, then frob ticket show --json reports priority high -- one round-trip test per folded field"
bound = false

[[acceptance]]
text = "Given the same fixture ledger and the same value, when the deprecated frob ticket priority spelling and the new frob ticket set priority spelling each run, then the resulting ledger bytes are identical"
bound = false

[[acceptance]]
text = "Given git grep over .claude/ docs/ scripts/ src/ tests/ for each of the nine deleted spellings, when re-run at close, then every hit outside the shim definitions has been updated; ~/.claude/refs/frob.md hits are listed in the Done report instead"
bound = false
+++

POINTS: 2. Parent story T-4687. blocked_by T-4690 (needs the shim helper).
File-disjoint from T-4692 and T-4695 (those touch _cli_parsers/*.py and
__main__.py; this one touches only _cli_parsers/_ticket/** and
app/ticket_runner/**), so it runs in parallel with them.

MEASURED 2026-09-19: `frob ticket --help` lists 54 subverbs. Nine of them are
one-field setters that differ only in which field they write:
  priority  kind  component  label  tier  milestone  sprint  accept  body
All nine live in src/frob/_cli_parsers/_ticket/_metadata.py (794 lines) and all
nine have the same shape: resolve ticket, validate value, write field, commit.

FOLD INTO: the planned ticket set form (argument order to match the
existing setters' order -- state the chosen signature in the Done report). One
subverb replaces nine. Field validation stays per-field (kind, priority, tier
and milestone have real enums/format rules; do not weaken them into free text).

KEEP `body` SEPARATE if and only if it takes stdin or --body-file: a setter that
streams a file is not the same shape as a one-token field write. Measure it and
say which way it went.

`set-parent` is NOT in this list -- it takes a second ticket id and maintains a
graph edge, not a field. Leave it alone.

Shims: each of the nine deleted names keeps the T-4690 shim for one minor
version, printing the planned ticket set form.

POSITIVE CONTROL (acceptance): a round-trip test per field -- the planned ticket set form followed by `frob ticket show T-xxxx --json` asserting the
field actually changed; plus a test that the deprecated `frob ticket priority`
spelling produces the identical ledger bytes as the new spelling on the same
fixture ledger. Same-bytes is the control that proves the fold is behaviour-
preserving rather than merely non-crashing.

CITATION SWEEP: `git grep` for each deleted spelling across .claude/, docs/,
scripts/, src/, tests/ -- the agent playbooks in .claude/ call these constantly
and a missed citation is a broken fleet. ~/.claude/refs/frob.md is OUT OF SCOPE;
report the edits it needs.

FILES (declared scope):
  src/frob/_cli_parsers/_ticket/__init__.py, _metadata.py
  src/frob/app/ticket_runner/__init__.py, _lifecycle.py
  tests/unit/test_ticket_set.py (new)

## Reopen log
- 2026-09-22: accidentally re-closed by a stale scope-mirror from the worktree before merging the coordinator's own reopen commit -- re-reopening, no code on dev, must land properly

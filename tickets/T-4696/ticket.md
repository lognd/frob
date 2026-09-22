---
id: T-4696
title: 'Nine ticket field-setters become one: frob ticket set field value (priority
  kind component label tier milestone sprint accept body)'
state: done
kind: feature
origin: human
created: '2026-09-19'
priority: medium
blocked_by:
- T-4690
parent: T-4687
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_ticket/__init__.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/app/ticket_runner/_lifecycle.py
- tests/unit/test_ticket_set.py
- src/frob/app/_config_external.py
- src/frob/app/ticket_runner/_ledger_mirror.py
- src/frob/strata/_assume_template.py
- docs/modules/vet.md
- src/frob/tickets/_leases.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/_config_external.py
  reason: frob ticket set needs its two new string fields (ticket_set_field, ticket_set_value)
    added to the from_external field-copy allowlist, the same T-4690 gap found (doctor_whereis
    silently no-op'd without this)
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/app/ticket_runner/_ledger_mirror.py
  reason: every verb in _ticket_dispatch_table() must declare a LEDGER_VERB_STRATEGY
    entry (T-2603) -- the new set verb needs one
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/strata/_assume_template.py
  reason: 'land''s unscoped pre-commit-merge-preview sweep refused T-4696 on repo-wide
    drift accumulated on dev since this worktree branched (neither file is T-4696''s
    own edit) -- coordinator directive: fix each finding at its root regardless of
    prior declared scope'
  actor: logan
  at: '2026-09-22'
- op: add
  glob: docs/modules/vet.md
  reason: 'land''s unscoped pre-commit-merge-preview sweep refused T-4696 on repo-wide
    drift accumulated on dev since this worktree branched (neither file is T-4696''s
    own edit) -- coordinator directive: fix each finding at its root regardless of
    prior declared scope'
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: land's unscoped pre-commit-merge-preview sweep flagged the same Class::method
    DRIFT002 bug the other T-4690-family lands already fixed elsewhere; T-5121 (the
    ticket that previously held this file's lease) is now done, so this file is free
  actor: logan
  at: '2026-09-22'
- op: add
  glob: design/frob.strata
  reason: 'SELFAUDIT001: _resolve_set_reason''s new --reason-file read_text call is
    a real fs.read site on _lifecycle.py the cli node hadn''t declared yet (fs.write
    already was, from earlier tickets) -- declaring it'
  actor: logan
  at: '2026-09-22'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.534.0
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
- field: priority
  old_value: high
  new_value: high
  reason: smoke test T-4696 set verb
  actor: logan
  at: '2026-09-22'
- field: priority
  old_value: high
  new_value: high
  reason: smoke test T-4696 set verb round-trip
  actor: logan
  at: '2026-09-22'
- field: priority
  old_value: high
  new_value: medium
  reason: revert smoke test
  actor: logan
  at: '2026-09-22'
body_changes:
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 2270
  new_length: 2270
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 2270
  new_length: 2270
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 2270
  new_length: 2270
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 2270
  new_length: 2270
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 2270
  new_length: 2270
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 2270
  new_length: 2270
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously;
    the bodies were written against predicted ids)'
  actor: logan
  at: '2026-09-19'
  old_length: 2270
  new_length: 2270
- mode: set
  reason: '2026-09-19: rewrite with the real leaf ids (drafts promoted non-contiguously)'
  actor: logan
  at: '2026-09-19'
  old_length: 2270
  new_length: 2270
- mode: set
  reason: 'DOC006: planned or rejected CLI forms written as prose so unrelated lands
    are not refused'
  actor: logan
  at: '2026-09-19'
  old_length: 2270
  new_length: 2246
evidence:
- tests/unit/test_ticket_set.py::TestSetRoundTrip::test_priority
- tests/unit/test_ticket_set.py::TestSetRoundTrip::test_kind
- tests/unit/test_ticket_set.py::TestSetRoundTrip::test_component
- tests/unit/test_ticket_set.py::TestSetRoundTrip::test_tier
- tests/unit/test_ticket_set.py::TestSetRoundTrip::test_milestone
- tests/unit/test_ticket_set.py::TestSetRoundTrip::test_sprint
- tests/unit/test_ticket_set.py::TestDeprecatedShimByteIdentical::test_priority_shim_matches_set
- tests/unit/test_ticket_set.py::TestCitationSweep::test_no_markdown_code_fence_recommends_a_deleted_field_setter
designated_repro_test: null
acceptance:
- text: Given a fixture ledger, when frob ticket set priority high runs on a ticket,
    then frob ticket show --json reports priority high -- one round-trip test per
    folded field
  evidence:
  - tests/unit/test_ticket_set.py::TestSetRoundTrip::test_priority
  - tests/unit/test_ticket_set.py::TestSetRoundTrip::test_kind
  - tests/unit/test_ticket_set.py::TestSetRoundTrip::test_component
  - tests/unit/test_ticket_set.py::TestSetRoundTrip::test_tier
  - tests/unit/test_ticket_set.py::TestSetRoundTrip::test_milestone
  - tests/unit/test_ticket_set.py::TestSetRoundTrip::test_sprint
- text: Given the same fixture ledger and the same value, when the deprecated frob
    ticket priority spelling and the new frob ticket set priority spelling each run,
    then the resulting ledger bytes are identical
  evidence:
  - tests/unit/test_ticket_set.py::TestDeprecatedShimByteIdentical::test_priority_shim_matches_set
- text: Given git grep over .claude/ docs/ scripts/ src/ tests/ for each of the nine
    deleted spellings, when re-run at close, then every hit outside the shim definitions
    has been updated; ~/.claude/refs/frob.md hits are listed in the Done report instead
  evidence:
  - tests/unit/test_ticket_set.py::TestCitationSweep::test_no_markdown_code_fence_recommends_a_deleted_field_setter
threat: null
component: cli
labels:
- cli-debloat
- points-2
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-4696
branch: t-4696
---
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
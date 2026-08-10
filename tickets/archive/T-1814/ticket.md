---
id: T-1814
title: Land silently drops non-release pyproject.toml edits (field-granular reset)
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land_release.py
- src/frob/tickets/_land_squash.py
- tests/test_ticket_land.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001/SYS100 requires declaring the new fs.write capability _reset_pyproject_version_field_only
    adds to _land_release.py
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_ticket_land.py::TestLand::test_non_version_pyproject_edit_survives_land
designated_repro_test: null
threat: null
component: null
---
Land silently drops non-release edits to pyproject.toml and still reports
success. `_land_release._reset_release_artifacts_to_pre_land` discarded
the ENTIRE contents of pyproject.toml/CHANGELOG.md/.frob-release.json
(whatever the squash staged for them) back to pre_land_tip, and
`_land_squash`'s completeness assertion subtracted exactly those three
filenames from its own missing-file check -- so the one guard that would
notice a dropped edit was told to ignore exactly the files the reset
discards.

Confirmed instance: T-1508's entire deliverable was a one-line dependency
pin in pyproject.toml (`smt = ["z3-solver>=4.13,<4.15.5"]`). It landed
`done` with that line reverted to unbounded, leaving main incoherent
(uv.lock pinned to the bound the code needed, pyproject.toml not),
re-dirtying root on every `uv run` and stalling the fleet. Confirmed
reproducible across four separate land attempts (T-1508, T-1810, and two
re-applies), all reporting `verified=True`.

Root cause: pyproject.toml is only PARTIALLY land-owned. The scaffolded
pre-commit hook (src/frob/scaffold/project.py) refuses a worktree commit
touching pyproject.toml only when the `version = ` line itself changes --
every other field ([project.optional-dependencies], [tool.*],
[build-system], entry points, ...) is legitimate worktree-agent
territory. CHANGELOG.md and .frob-release.json are, by contrast, wholly
land-owned in practice (the hook refuses ANY worktree commit touching
CHANGELOG.md at all; .frob-release.json is a wholly land-derived
manifest).

Fix: narrow `_reset_release_artifacts_to_pre_land`'s pyproject.toml reset
to FIELD granularity -- rewrite only the `version = "..."` line back to
pre_land_tip's value, leaving every other line (and therefore every
other field) exactly as the squash staged it. CHANGELOG.md and
.frob-release.json keep the existing whole-file reset (both are
hook-refused or wholly derived, so whole-file reset there was never the
bug). The completeness-assertion subtraction in `_land_squash.py` needs
no code change once the reset itself is field-scoped: a real non-version
pyproject.toml edit survives the reset and stays staged, so it is never
actually in the "missing" set to begin with; the subtraction only ever
discharges the genuine version-only no-op case going forward.

Required, non-optional: a regression test that lands a ticket whose ONLY
change is a non-version pyproject.toml edit and asserts the edit is on
main afterwards. Owed follow-up per the coordinator: re-land the bound
z3-solver pin (`smt = ["z3-solver>=4.13,<4.15.5"]`) as the end-to-end
verification case once this fix is in place.

## Done report

Narrowed `_reset_release_artifacts_to_pre_land`'s reset of pyproject.toml
from whole-file to FIELD-granular: `_reset_pyproject_version_field_only`
now rewinds only the `version = "..."` line back to pre_land_tip's value,
leaving every other line -- and therefore every other field a landing
ticket legitimately touched ([project.optional-dependencies], [tool.*],
[build-system], entry points) -- exactly as the squash staged it.
CHANGELOG.md and .frob-release.json keep the original whole-file reset:
both are hook-refused (CHANGELOG.md) or wholly land-derived
(.frob-release.json) in practice, so the whole-file reset was never the
source of the bug for either. No code change was needed in
_land_squash.py's completeness-assertion subtraction -- it composes
correctly with the field-scoped reset automatically: a real non-version
pyproject.toml edit now survives the reset and stays staged, so it is
never in the "missing" set to begin with; the subtraction only still
discharges the genuine version-only no-op case.

Verified the confirmed mechanism directly: reverted the fix locally,
re-ran the new regression test, watched it fail with the exact silent-
drop shape (edit present in the worktree commit, absent from the landed
main commit, `land()` still returning `Ok`) -- then restored the fix and
confirmed the same test passes.

Regression test added: TestLand.test_non_version_pyproject_edit_survives_land
in tests/test_ticket_land.py -- lands a ticket through the real `land()`
entry point whose ONLY change is a non-version pyproject.toml field (a
z3-solver dependency-pin edit, the exact shape of T-1508's confirmed real
instance), with bump_version supplied (Ok(None), no bump needed) so the
reset path actually runs, and asserts the edit is on main afterward while
the version field itself is untouched.

Closed-ticket sweep (required by the ticket): searched tickets.md +
tickets-archive.md for every DONE ticket whose declared scope named
pyproject.toml, CHANGELOG.md, or .frob-release.json (94 hits). This exact
bug was introduced by T-1760 (commit 4d23838e4) -- cross-referencing
against every `land T-####` commit reachable after that commit found ZERO
overlap: every one of the 94 scope hits landed BEFORE T-1760 shipped the
whole-file reset, so none of them could have hit this exact regression.
T-1508 (the confirmed real instance, currently `state: queued` in
tickets.md after being dropped four times) is the only affected ticket
found. Re-landing its bound z3-solver pin
(`smt = ["z3-solver>=4.13,<4.15.5"]`) as the end-to-end verification case
is owed follow-up work per the coordinator's brief, tracked by T-1508
itself -- not folded into this ticket's own scope.

### Changed
```
 tickets/T-1814/done-report.md | 59 +++++++++++++++++++++++++
 tickets/T-1814/ticket.md      | 76 +++++++++++++++++++++++++++++++++
 2 files changed, 135 insertions(+)
```

### Evidence
- `tests/test_ticket_land.py::TestLand::test_non_version_pyproject_edit_survives_land` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 2 error(s), 968 warning(s), 733 waived
- error-findings: ARCH001@src/frob/tickets/_new_renumber.py, invalid-return-type@src/frob/tickets/_new_renumber.py

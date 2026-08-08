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

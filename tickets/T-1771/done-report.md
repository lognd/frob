## Done report

The core `_ensure_uv_lock_coherent` fix (comparing `uv.lock`'s recorded
frob version against `pyproject.toml` unconditionally) had already
landed by the time this ticket was picked up, but the "unconditionally"
claim was not quite true: `_ensure_uv_lock_coherent` was called ONLY
from inside `_ensure_release_quartet_coherent`'s pyproject-vs-manifest
DIVERGENCE branch. The common, healthy case -- pyproject.toml and
`.frob-release.json` already agree, `bump_version` reported `Ok(None)`
because nothing needed to change -- skipped the lock check entirely,
which is exactly the gap the ticket's own "remaining work item 1" names
("a land whose bump_version returns Ok(None) ... must leave the lock in
step"). Fixed: the lock check now runs whenever `pyproject_version` is
known at all, a sibling of the manifest check rather than nested inside
it (split into `_resync_manifest_if_diverged` to keep the parent under
ARCH001's line threshold).

Item 1 (regression coverage for the real shape): added
`TestUvLockCoherenceWhenAlreadyBumped` with a fake `run_argv` that
actually rewrites `uv.lock`'s on-disk content (not a no-op mock), so the
test asserts the lock's own RECORDED VERSION via
`_read_working_uv_lock_version` after the call, per the ticket's own
instruction -- not merely that a sync helper was invoked. A companion
test asserts an already-coherent lock triggers no `uv lock` spawn at
all.

Item 2 (audit CHANGELOG.md, decide and write down where it belongs):
REL001 (`frob.gates.release_gate`) already refuses with "no CHANGELOG.md
entry for {version}" at GATE time -- it was never actually missing
coverage, just undocumented that this was the deliberate split. Written
down in both `_ensure_release_quartet_coherent`'s own docstring and
`docs/modules/tickets.md`'s T-1358/T-1771 note: the other three quartet
members get a land-time auto-resync because there is one correct
version NUMBER to force-write; CHANGELOG.md gets a gate-time refusal
instead because there is no single correct PROSE entry to auto-write.

Item 3 (rename or fix the docstring): fixed the docstring rather than
renaming `_ensure_release_quartet_coherent` -- a rename would touch
every caller and test referencing the name for no functional gain, and
the docstring now states explicitly which three members this function
checks and where the fourth is checked instead.

### Changed
```
 docs/modules/tickets.md                   | 16 ++++++++
 src/frob/tickets/_land_release.py         | 52 ++++++++++++++++++++++---
 tests/unit/test_land_release_coherence.py | 65 +++++++++++++++++++++++++++++++
 tickets/T-1771/ticket.md                  | 18 ++++++++-
 4 files changed, 144 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/test_land_release_coherence.py::TestUvLockCoherenceWhenAlreadyBumped::test_stale_lock_resynced_even_when_pyproject_and_manifest_agree` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_coherence.py::TestUvLockCoherenceWhenAlreadyBumped::test_lock_already_coherent_is_untouched` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 882 warning(s), 726 waived
- error-findings: none (measured, zero errors)

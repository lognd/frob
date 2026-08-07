## Done report

T-0731 delivers the three-part land-ownership mandate.

(1) REL001 suppression under FROB_AGENT: `release_gate` in
src/frob/gates/__init__.py now calls `_rel001_bump_suppressed_under_agent`
(checks `os.environ.get("FROB_AGENT")`) before computing the bump/changelog
half of REL001. When set, it logs a one-line note ("version bump is a
land-time step") and skips the bump-required and missing-changelog
violations entirely, while still computing `bump` via `diff_class` for
logging. The open-debt (T-0412) and expired-deprecation (T-0576) halves of
`release_gate` are untouched and still fire under FROB_AGENT -- those are
real release blockers, not bump-and-chase busywork.

(2) Land-time changelog/bump ownership: already implemented under T-0338
(`_apply_release_bump_for_land`/`_write_release_bump` in
src/frob/app/ticket_runner.py, invoked via `_land.py`'s injected
`bump_version` callback) -- `frob ticket land` computes the version bump
and auto-generates a `## [version] - unreleased` CHANGELOG.md entry naming
the ticket id/title, staging pyproject.toml/CHANGELOG.md/.frob-release.json
together in the squash commit. Verified this already satisfies the
ticket's item 2 acceptance; no new code needed there. Per the ticket's own
coordination note, `ticket_runner.py`/`tickets/__init__.py` were left
untouched (T-0749 is concurrently editing the evidence --accepts path
there).

(3) Mechanical guard: extended the T-0431/T-0577 `pre-commit` hook (already
carrying the FROB_AGENT and raw-ticket-merge guards) with a third script,
`_FORBID_LAND_OWNED_FILES_SCRIPT` (src/frob/scaffold/project.py), installed
by the same `install_worktree_lease_hook`/`apply_managed_blocks`
(_managed.py) path. It refuses a worktree commit whose staged files
include CHANGELOG.md, uv.lock, or a `pyproject.toml` diff touching the
`version = "..."` line specifically, unless FROB_LAND_INTERNAL=1 is set
(the same escape hatch T-0577 established). tickets.md gets a WARNING, not
a refusal, on the same commit -- documented v1 heuristic per the ticket's
own text (reliably distinguishing a CLI-written ledger change from a
hand-edit from inside a shell hook is not solved).

(4) Playbook: added section 4b ("Land-owned files are untouchable in a
worktree (T-0731)") stating the blacklist plainly and explaining why the
old per-worktree bump dance is gone, not just discouraged. No prior
"bump-and-chase" instructions existed in the playbook text itself to
delete (that phrasing/history lived in code comments, not the playbook),
so this is a net-new section rather than a replacement.

Cuts/notes: no `--stamp-baseline`/`--delta` triage was possible -- no
baseline existed in this worktree and stamping one now would have folded
this ticket's own changes into the baseline, defeating the point; relied
on `frob check --only <group> --ticket T-0731` per group instead (all
green except two pre-existing, out-of-scope items: a `ty` diagnostic in
tests/system/test_cli_doctor.py, and TICK006/TICK003 ledger findings that
predate this branch). uv.lock briefly showed as modified during work --
purely a `uv run` self-resync of the editable package's own version entry
to match pyproject.toml (already at 0.93.0 from the T-0731 warm-up merge,
not a bump I performed) -- checked out back to HEAD before every commit,
never staged.

### Changed
```
 docs/guides/agent-playbook.md              |  36 ++++++
 src/frob/gates/__init__.py                 |  43 ++++++-
 src/frob/scaffold/_managed.py              |   3 +
 src/frob/scaffold/project.py               |  71 +++++++++++-
 tests/test_gates.py                        |  64 +++++++++++
 tests/test_scaffold_worktree_lease_hook.py | 177 +++++++++++++++++++++++++++++
 tickets.md                                 | 149 +++++++++++++++++++++++-
 7 files changed, 530 insertions(+), 13 deletions(-)
```

### Evidence
(no evidence recorded)

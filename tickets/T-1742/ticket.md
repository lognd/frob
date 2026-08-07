---
id: T-1742
title: pre-commit land-owned-file guard refuses legitimate git merge main commits
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/scaffold/_managed.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The scaffolded `.git/hooks/pre-commit` (T-0431/T-0731's land-owned-file
guard) has no exemption for an ordinary `git merge main` merge commit --
it refuses ANY commit whose staged file list contains CHANGELOG.md,
uv.lock, or a pyproject.toml version-line diff, with no check for
whether MERGE_HEAD exists or whether the staged content is byte-
identical to main's own copy (the common case: a worktree merging main
forward legitimately carries main's own land-generated changes to these
files, with zero local divergence).

Hit directly today: `git merge main` in a long-lived worktree pulled
forward several of main's own lands (each of which legitimately bumped
CHANGELOG.md/pyproject.toml/uv.lock), and the resulting merge commit
was refused outright by the hook, even though `git diff main -- \
CHANGELOG.md pyproject.toml uv.lock` was empty (the merged content
exactly matched main -- no hand-edit, no divergence, nothing for the
guard to actually be protecting against). Worked around this once with
`FROB_LAND_INTERNAL=1` for that single commit after verifying byte-
identity to main first; the playbook explicitly says this env var
should never be set by a worktree agent, so this was a one-off, not a
repeatable answer.

Fix: exempt the guard when `$(git rev-parse -q --verify MERGE_HEAD)`
succeeds (a real merge commit in progress), or narrow it further to
only refuse when the staged content of the land-owned file actually
DIFFERS from main's current tip (a hand-edit, not a merge fast-
forwarding main's own history). Either fix removes the false refusal
without weakening the guard against the real hazard (T-0731: a
worktree agent hand-editing these files itself).
---
id: T-0478
title: 'recover/finish ''frob bind'' command + pybind11/pyo3 project-init scaffolding:
  WIP preserved on branch worktree-agent-a27be33c289e10301 (commit fca2851) -- src/frob/bind/
  + app/bind_runner.py + init/data/*.j2 templates + init/project.py wiring, abandoned
  uncommitted in an orphaned WSL-path worktree; evaluate and either land or drop'
state: dropped
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
dropped 2026-07-21: commit fca2851 does not exist anywhere in this repo's
object store, same as T-0477's sibling drop. The named branch
worktree-agent-a27be33c289e10301 turns out to point to the EXACT SAME
commit as T-0477's branch (`7b88b776738f5e76fd5423542ab6e175eb3a964d`,
verified via `git rev-parse` on both refs) -- unrelated CI-template work,
already a merged ancestor of main, with `git diff
main...worktree-agent-a27be33c289e10301 --stat` empty. Neither preserved
branch actually retains the described WIP; both orphaned worktrees lost
their uncommitted state.

Reconciled against current main per the ticket's own instruction: both
halves this ticket describes already exist today, built during the
rework era under different names than the WIP predates --
(1) `frob bind` is a full subcommand (`src/frob/bind/__init__.py`,
`src/frob/app/bind_runner.py`, listed in `frob --help`) that "verifies
binding declarations match source signatures" (pybind11/PyO3 BIND
comment verification), and (2) pybind11/pyo3 project-init scaffolding
lives under `frob scaffold` (the successor to the WIP-era `init`
subsystem): `src/frob/scaffold/data/types/pybind11-library/*.j2` and
`src/frob/scaffold/data/types/pyo3-library/*.j2`, wired into the
`_MANIFESTS` table in `src/frob/scaffold/project.py` (e.g. line ~227,
`"pybind11-library": [...]`), covering pyproject.toml, Makefile,
frob.toml, CMakeLists.txt, C++ src/include, bindings.cpp, Python
package init, and tests. There is nothing to land -- both requested
capabilities ship on main under `bind`/`scaffold`, and there is no
reachable WIP diff to port over them. No evidence required for a
dropped ticket per playbook precedent (T-0475, T-0477).
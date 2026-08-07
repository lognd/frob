## Done report

Changed:
docs/guides/agent-playbook.md (new -- the per-dispatch checklist: worktree
warm-up incl. `git merge main` + tip verification, `make core` natives,
`uv run frob` discipline, never-pipe-verifying-commands rule, scope
conventions, evidence recording incl. the T-0167 CLI-dispatch-test
precedent for docs-only tickets, gate measurement via `frob check --delta`
+ `--stamp-baseline`, waive discipline, Done-report requirements, the
deletion-filter land rule with the T-0167 stale-merge incident cited,
ledger-conflict splice guidance, ticket workflow, style)
docs/index.md (new bullet under Getting started linking the playbook)
CLAUDE.md (appended pointer section directing every worktree agent to read
the playbook first; original rework brief left untouched, out of this
ticket's remit)
Makefile (`playbook` target added to .PHONY and the target list, `cat`s
docs/guides/agent-playbook.md -- judgment call: the Makefile's style favors
thin `$(STAMP)`-guarded targets that shell out to `uv run`, but a doc
pointer needs no venv, so this target skips the stamp dependency and just
cats the file)
tickets.md (this Done report)

Investigated but NOT implemented (disclosed per plan's "ALSO" item):
shared-natives inheritance across worktrees (CARGO_TARGET_DIR sharing or a
wheel cache reused by `make core`) was investigated only to the point of
confirming the current cost (`make core` in this fresh worktree took ~34s
of `cargo build --release` for strata-core alone, from-scratch, per the
`make core` run performed for this ticket) and documenting that fact plus
the general mechanism options in the playbook's warm-up section (item 1).
No `CARGO_TARGET_DIR` wiring or wheel-cache mechanism was built -- that is
real implementation work (Makefile + possibly CI cache plumbing) beyond a
docs ticket's scope, and is called out explicitly in the playbook rather
than silently dropped.

Evidence: tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
(ran directly: `uv run pytest tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches -q -o addopts=` -> `1 passed in 0.95s`; recorded via `frob ticket evidence`), per the T-0167 precedent for docs-only tickets with no pytest surface of their own. `frob test --base main` (touched-set) reports `nothing touched selects any test` for the five touched files (CLAUDE.md, Makefile, docs/guides/agent-playbook.md, docs/index.md, tickets.md all resolve as `unbound file ... has unknown language` -- expected for markdown/Makefile-only changes, no test-file endpoint exists to select).
Filed: none (the shared-natives mechanism is documented as future work in the playbook itself, not filed as a separate ticket since T-0175's own "ALSO" clause already tracks it and re-filing would duplicate)
Gates: `uv run frob check --ticket T-0175 --json`: gates stage exit_code=0, zero error-severity diagnostics (PRE001 refreshed via `frob ticket sweep T-0175` after editing past the initial pre-work sweep). ruff-check/ruff-format/ty/frob-cycle/frob-dup/frob-arch/frob-exports(all packages): all exit_code=0. TEST006 (no coverage stamp) is the pre-existing campaign-wide warn, not re-stamped per instruction (never run `make coverage`). `ruff check src/ tests/` under the project-pinned `uv run ruff` (0.15.16): "All checks passed!" -- no Python source was touched by this ticket so PATH-ruff (0.14.10) parity is moot for this diff (running it against docs/Makefile produces nonsense non-Python-syntax noise, not a real signal).

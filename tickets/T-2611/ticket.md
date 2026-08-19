---
id: T-2611
title: core.autocrlf=true puts CRLF in every source file, silently breaking any length
  or byte-level measurement
state: in-progress
kind: bug
origin: human
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .gitattributes
- tests/unit/test_gitattributes_crlf_normalization.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_gitattributes_crlf_normalization.py
  reason: regression lock proving the repo-wide eol=lf normalization is declared and
    effective
  actor: logan
  at: '2026-08-19'
evidence:
- tests/unit/test_gitattributes_crlf_normalization.py::TestGitattributesEolNormalization::test_sampled_source_files_are_pinned_to_lf
- tests/unit/test_gitattributes_crlf_normalization.py::TestGitattributesEolNormalization::test_attachment_binary_pin_still_holds
- tests/unit/test_gitattributes_crlf_normalization.py::TestGitattributesEolNormalization::test_rapid_debt_lease_pin_still_holds
designated_repro_test: tests/unit/test_gitattributes_crlf_normalization.py::TestGitattributesEolNormalization::test_sampled_source_files_are_pinned_to_lf
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Measured

    git config --get core.autocrlf   ->  true      (a WINDOWS setting, on WSL/Linux)
    60 of 60 sampled tracked src/frob/*.py files contain CR in the WORKING TREE

T-2586 pinned `text eol=lf` for `rapid-debt.jsonl` and
`force-overrides.jsonl` -- the two files whose churn was then visible. That
fix was correct and should stay. But the underlying cause is repo-wide:
with `core.autocrlf=true` and no `.gitattributes` normalization for source,
git writes CRLF into the working tree for essentially every tracked text
file.

## Why this is a correctness hazard, not a cosmetic one

Tools that strip line endings (git, ruff, python) are unaffected. Ad-hoc
measurement is NOT, and this fleet measures constantly.

LIVE INCIDENT, this session. Checking for E501 violations with

    awk 'length($0)>88'

reported four over-length lines in `src/frob/scaffold/project.py` and one
in `src/frob/app/ticket_runner/_ledger_mirror.py`. `ruff check --select
E501` reports BOTH FILES CLEAN. The lines are exactly 88 characters plus a
CR, and `awk` counted the CR. `cat -A` confirms: `...lease for \^M$`.

That faulty measurement produced a real, wrong artifact: T-2596 was filed
claiming "four real E501 lines", when one genuine finding existed. An agent
then correctly fixed the one real finding and correctly reported the others
as absent -- and the coordinator briefly read that accurate report as a
false green, because the coordinator's own oracle was the broken one.

Any length check, byte-offset check, column number, or hand-rolled diff
against the working tree is off by one per line, silently, in the direction
of over-reporting.

## Fix

Add repo-wide `.gitattributes` normalization -- `* text=auto eol=lf`, or an
equivalent explicit set -- so the working tree gets LF regardless of any
per-clone `core.autocrlf`. This must live in `.gitattributes` and not in a
`git config` change: a config change does not travel with the repo, and a
fresh clone silently gets the broken behavior. That is the same argument
that chose a BUILT-IN merge driver for `rapid-debt.jsonl` and the same one
T-2586 applied to its two files; this generalizes it.

Re-normalize the working tree after adding it (`git add --renormalize .`).

## Sequencing -- this needs a QUIET WINDOW

Renormalizing rewrites the working-tree copy of essentially every tracked
file. Doing that while agents hold worktrees and lands are in flight risks
enormous spurious conflicts. Coordinate before landing: confirm zero lands
in flight and ideally no active agent worktrees. This is a legitimate case
for serializing the fleet.

## Positive controls, both directions

- after the fix, a freshly checked-out source file contains NO CR
  (`grep -c $'\r' <file>` is 0)
- `awk 'length($0)>88'` and `ruff check --select E501` AGREE on the same
  file -- this is the specific defect being closed, and the check that
  proves it
- `git status` is clean immediately after renormalization -- a
  renormalization that leaves the tree permanently dirty has failed
- the T-2586 pins for `rapid-debt.jsonl`/`force-overrides.jsonl` still hold
  and those files still report clean

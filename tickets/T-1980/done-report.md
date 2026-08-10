## Done report

Changed:
- docs/guides/frob-version-policy.md (new) -- the recorded upgrade
  policy, staged rollout sequence, and measured typani delta
- docs/index.md -- one inbound link to the new guide, same convention
  every other docs/guides/ entry follows

Kind changed bug -> docs: this ticket's actual deliverable is a policy
record plus a read-only measurement, no code fix, matching the T-1031/
T-1071 estate-rollout precedent (also kind=docs). bug-kind would have
required a BUG002 pytest repro that could pass/fail at parent, which
does not fit a policy decision.

MEASUREMENT (the core deliverable): ran this repo's own 0.433 build
(`uv run frob check /home/logan/projects/typani --only gates --json`)
and the stale global 0.184 build (`frob check /home/logan/projects/
typani --only gates --json`, bare PATH binary) against typani, no
`--fix`, no `--stamp-*` flags. Confirmed BEFORE running either that
plain `frob check` (no `--fix`) never writes tracked content -- the
only writes are to typani's own gitignored `.frob/` cache, same as any
normal invocation in any repo -- and diffed `git status --short` on
typani before/after both runs: unchanged (still only the pre-existing
dirty tickets.md/uv.lock this ticket's own filing already found).

Result: 0.184 = 27 errors/70 warnings. 0.433 = 40 errors/59 warnings.
Every one of the +13 new errors comes from two gate families that did
not exist at 0.184 at all (OPAQUE001 +5, SUPPRESS001 +8) -- NOT from an
existing gate getting stricter on previously-passing code. typani's
`frob check` is already non-zero-exit under the CURRENT stale build (27
pre-existing errors); upgrading adds findings to an already-red gate,
it does not flip a green one red. Warnings decreased by 11 (not
independently triaged, noted as out of scope in the doc).

Policy recorded: do not run `uv tool upgrade frob` as a ticket-drain
side effect; staged rollout is measure-one-repo -> human review ->
upgrade once, globally -> re-verify -> roll out to the remaining 7
repos one at a time, each with its own dirty-ledger triage (explicitly
NOT auto-committed by this ticket or the upgrade). Full sequence in
docs/guides/frob-version-policy.md.

Filed: T-1990 (real id renumbers at land) -- FIX DIRECTION
point (c) from T-1980's own body (making version skew self-announcing
at the repo level in frob's own code, not one machine's Claude Code
hook config) is genuine code work with its own BUG002-shaped acceptance
test, out of this docs-only ticket's scope. Cited in the policy doc.

Evidence: 1 evidence-cmd entry (`frob ticket evidence --evidence-cmd`,
docs-kind channel) -- greps the policy doc for the three load-bearing
measured facts (both new-gate deltas and the 27/40/+13 total) so the
binding is not a silent no-op grep -q, satisfying T-1892's
zero-information-digest refusal.

Gates: `frob check --ticket T-1980` is 0 errors on every ticket-relevant
gate family after narrowing scope to the specific files touched
(docs/guides/frob-version-policy.md, docs/index.md, tickets/T-1980/**,
tickets/T-1990/** for the follow-up ticket this ticket files)
and re-sweeping. Remaining ruff-check/ruff-format FAILs in the same run
are pre-existing repo-wide drift, unrelated to this change (confirmed:
same 91-file count, same single F401 in an unrelated test file, present
before this ticket touched anything).

Confirmed modified nothing outside this repo: `git status --short` in
typani is unchanged before/after both measurement runs (still only the
pre-existing dirty tickets.md/uv.lock this ticket's own filing
originally found, nothing new). No sibling repo's tracked files, ledger,
or any other content was touched. The global `frob` install
(`/home/logan/.local/bin/frob`, still 0.184.0) was not upgraded, pinned,
or otherwise modified.

### Changed
```
 tickets/T-1980/ticket.md           | 48 +++++++++++++++++++++++++++++++++---
 tickets/T-1990/ticket.md | 50 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 95 insertions(+), 3 deletions(-)
```

### Evidence
- `cmd:grep -n 'OPAQUE001. (+5)\|SUPPRESS001. (+8)\|| errors | 27 | 40 | +13 |' docs/guides/frob-version-policy.md exit=0 sha256=7c1286b47ae3` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: F401@/home/logan/projects/frob/.claude/worktrees/version-skew/tests/unit/test_tickets_evidence_only_scope.py

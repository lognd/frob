## Done report

Added `.gitattributes` entries routing `rapid-debt.jsonl` AND
`force-overrides.jsonl` (the sibling tracked-root append-only ledger,
frob.tickets._force_override, T-1762 -- covered proactively even though
it does not exist on disk yet in this repo) through git's built-in
`merge=union` driver, anchored with a leading slash per the existing
`.gitattributes` anchoring precedent. Chose union over a new frob merge
driver deliberately: union IS append-only "keep both sides" semantics,
and needs no per-clone `git config` registration the way `merge=frob-
ledger` does -- a worktree that skipped that setup silently falls back
to the default conflicting driver, exactly the failure mode this ticket
exists to close.

Audited every tracked `.jsonl` (`git ls-files "*.jsonl"`): only
`rapid-debt.jsonl` is currently tracked. Searched further for other
tracked, root-level, append-only artifacts by grepping for `open(path,
"a"` writes across src/frob -- found `force-overrides.jsonl` (same
shape, added above) and `.frob/coverage-lock-audit.log` /
`.frob/telemetry.jsonl` (both under the gitignored `.frob/` directory,
never tracked, no merge concern). No other tracked append-only file
found; nothing left needing a follow-up.

Verified by REPRODUCTION (tests/unit/test_gitattributes_merge.py), not
inspection: two branches each append a different record to
`rapid-debt.jsonl`; a real `git merge` reports a clean merge (exit 0,
empty `git status --porcelain`) with both records present and zero
conflict markers.

Investigated item 4 (can union merge duplicate a shared line): measured
directly with a second reproduction test -- when both sides append the
BYTE-IDENTICAL line, git's union driver keeps exactly one copy, not two
(deduplicates, does not duplicate). Harmless for this file's shape (every
real record embeds a unique commit sha; an exact duplicate can only arise
from a retry re-emitting an identical record for the same commit, and
collapsing it to one entry is correct). No dedup-on-read pass added --
this was a measured finding, not a speculative mitigation, per the
ticket's own explicit instruction not to add one speculatively.

Documented the resolution in docs/modules/tickets.md, next to the
existing "Git merge driver" section, under a new "rapid-debt.jsonl merge
rule (T-1873)" heading. Dropped an accidental `T-0480` ticket-id citation
from that new prose after DOC011 flagged it as unresolvable -- T-0480
does not exist as a real ticket despite being referenced in
`.gitattributes`'s own pre-existing comment (historical, out of scope to
fix here); described the anchoring rule without citing a phantom id.

design/frob.strata: declared the new test file's `exec`/`fs.write`/
`fs.read` capabilities in the `testsuite` node's `may` lists (SELFAUDIT001
required this; `frob sys sync-interface` only manages `interface=` attrs,
not capability declarations, so this was a hand edit, not automatable).

Waived DUP001 on the new file's `_git_init`/`_commit_all` helpers --
byte-identical copies already exist, unwaived, in at least 3 other test
files pre-dating this one (tests/test_gates_tick005.py,
tests/test_serve_daemon.py, tests/test_ticket_merge_driver.py/
tests/test_ticket_land.py). Extracting a shared tests/conftest.py fixture
is a real, worthwhile follow-up but touches several other files, out of
this ticket's declared scope.

### Changed
```
 tickets/T-1873/done-report.md | 57 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1873/ticket.md      | 23 +++++++++++++++--
 2 files changed, 78 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_gitattributes_merge.py::TestRapidDebtUnionMerge::test_two_branches_appending_different_records_both_survive` (pytest node id, verified passing when recorded)
- `tests/unit/test_gitattributes_merge.py::TestRapidDebtUnionMerge::test_identical_line_appended_on_both_sides_deduplicates` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 1142 warning(s), 757 waived
- error-findings: none (measured, zero errors)

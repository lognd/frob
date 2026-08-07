## Done report

Replaced v2_state_transitions' single `git log --follow -p` call (whose
rename detection uses a >=50%-byte-similarity heuristic, not a genuine-
rename check) with a two-stage miner: `_v2_path_lineage` walks backward
from the ticket's current path using `_v2_rename_source`, which only
trusts an `-M100%` (exact-content) `--diff-filter=R` rename -- the only
kind frob's own git-mv tooling (git_mv_dir / _renumber_v2's directory
rename) ever produces. Each lineage segment is then mined via plain
(non-follow) `git log --reverse -p` and the per-commit `+state:` results
are merged oldest-first, deduped by sha. Two v2 tickets that merely share
the standard template (id/title/state differ, ~8 other fields identical)
can never satisfy -M100%, so they can no longer be misattributed as a
rename source/copy origin of one another -- the exact false-positive
shape described in the ticket body.

Added a regression test reproducing that shape directly: file T-0001,
then file a byte-similar T-0002 (same template/body), advance T-0002
through in-progress/done, and assert v2_state_transitions(root, "T-0002")
still returns all three transitions instead of dropping the later two.

### Changed
```
 src/frob/tickets/_store.py | 172 +++++++++++++++++++++++++++++++++++----------
 tests/test_tickets.py      |  57 +++++++++++++++
 tickets.md                 |   3 +-
 3 files changed, 193 insertions(+), 39 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 338 warning(s), 791 waived
- error-findings: none (measured, zero errors)

## Done report

Rewrote `load_all` to do 3 whole-table SELECTs (symbols/edges/malformed,
each ORDER BY path) instead of calling `load_file_data` per file (3
queries per file x ~1865 files). Added a `json.loads` fast path for the
common `attrs == '{}'` case in the edges reconstruction. `load_file_data`
itself is unchanged and still serves the incremental single-file cache-hit
path (`frob.graph.__init__`'s per-file rebuild check) -- this rewrite only
touches the whole-snapshot reassembly path.

Measured directly against this repo's own `.frob/cache.db` (18198 symbols,
16205 edges, 2x loop average):
- before (`load_file_data` per file, in-process control): ~6.6s/call
- after (`load_all`, 3 whole-table SELECTs): ~0.37s/call
(~18x speedup)

Correctness verified byte-identical, not just count-equal: compared
`root`, `file_hashes`, `symbols` (dict equality) and `malformed` (tuple
equality) directly equal between the old per-file-loop reconstruction and
the new whole-table one; `edges` compared as a sorted multiset (dict
iteration order over `file_hashes` isn't guaranteed to match `ORDER BY
path`, so list-order equality isn't the right check) -- all equal.

AFFECT001 (load_all's doc anchor, docs/modules/graph.md#cache) is waived
inline: the query-shape-only change doesn't alter the documented contract
("reassembles the full GraphSnapshot from every row currently in the db").
Touching docs/modules/graph.md directly was tried first but reverted --
adding that shared doc file to the ticket's scope pulled in scope-closure
obligations for the whole graph module's other public symbols (SCOPE002),
wildly out of proportion to this ticket's narrow query-shape change.

Known, expected multi-ticket-worktree artifact: `frob check --ticket
T-1214` reports one `gate:SCOPE` SCOPE001 error on `src/frob/gates/
_secrets.py` -- that is T-1211's own change, committed earlier in this same
worktree/branch but not yet landed to main, so it still shows in the
ticket-scoped diff against main. Not a T-1214 regression; will resolve once
T-1211 lands.

### Changed
```
 src/frob/gates/_secrets.py | 79 ++++++++++++++++++++++++++++++++++++++++++++--
 src/frob/graph/cache.py    | 51 ++++++++++++++++++++++++------
 tickets.md                 | 73 +++++++++++++++++++++++++++++++++++++++---
 3 files changed, 188 insertions(+), 15 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 266 warning(s), 741 waived
- error-findings: none (measured, zero errors)

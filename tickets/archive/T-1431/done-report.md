## Done report

T-1431: WIRE001 fired on a symbol a diff RELOCATES (a file split), because
the diff-scoped hunk proxy `_new_callable_records` cannot distinguish "this
diff DEFINED a symbol" from "this diff moved an existing symbol's whole
span into a new file" -- both look identical to a per-file line-range
check.

Fix: `_merge_base_body_match` (src/frob/gates/_dead_symbols.py) asks, for
each WIRE001 case-1 candidate that would otherwise fire, whether a
same-SHORT-NAME `def`/`class` existed ANYWHERE in the tree at the diff's
merge-base (`diff.base`, already the resolved sha `working_diff` computes)
with the SAME body (or, for a body-less symbol, signature) digest. A
`git grep` at the base revision finds name-match candidate paths cheaply;
only those pay for a `git show <base>:<path>` blob read plus a real
`frob.lang.parse_file` extraction (via a scratch temp file, since
`parse_file` only reads from a real `Path`) to compare digests against the
candidate's own `SymbolRecord.digests`. A digest match means the symbol was
RELOCATED, not introduced, and WIRE001 stays silent about it; a genuinely
new symbol (no prior name+digest match anywhere at the merge-base) still
fires exactly as before -- proven by a regression test that puts a
relocated symbol and a genuinely-new symbol in the SAME split-destination
file and asserts only the new one fires.

Two regression tests added to `tests/test_gates.py::TestWireGate`:
- `test_relocated_symbol_via_file_split_is_not_flagged`
- `test_genuinely_new_symbol_in_a_split_sibling_file_is_still_flagged`

Both use a real git repo fixture (`_git_init` + a real commit + branch +
uncommitted split), since the relocation check needs a real merge-base sha
to `git grep`/`git show` against -- the existing tests' synthetic
`Diff(base="x", ...)` fixtures are untouched and still pass (a fake base
ref makes `git grep`/`git show` fail cleanly, which `_merge_base_body_match`
treats as "no match", i.e. no relocation-exemption -- verified no existing
WIRE001 test regressed).

Scope: src/frob/gates/_dead_symbols.py, tests/test_gates.py -- both inside
T-1431's declared scope. No registry/gate-catalog changes (WIRE001's rule
id itself is unchanged; this narrows an existing gate's false-positive
surface, it does not add a new rule).

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py   |    68 +-
 src/frob/gates/_dead_symbols.py           |   251 +-
 tests/test_gates.py                       |   203 +
 tests/test_ticket_work_and_land_finish.py |    59 +
 tickets-archive.md                        | 20772 ++++++++++++++++++++--------
 tickets.md                                | 11000 ++-------------
 6 files changed, 16877 insertions(+), 15476 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestWireGate::test_relocated_symbol_via_file_split_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_genuinely_new_symbol_in_a_split_sibling_file_is_still_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 9 error(s), 878 warning(s), 694 waived
- error-findings: AFFECT001@src/frob/gates/_dead_symbols.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/gates/_dead_symbols.py, COV003@tickets/T-1378, COV003@tickets/T-1406, COV003@tickets/T-1408, COV003@tickets/T-1419, COV003@tickets/T-1423, PERF004@src/frob/gates/_dead_symbols.py

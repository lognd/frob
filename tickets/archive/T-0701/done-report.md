## Done report

Implemented SYS205 (`frob.strata._mode_conformance.check_mode_conformance`),
the code-level half of the T-0700/T-0701 resource-contention mandate:
joins each node's T-0700 `access "RESOURCE" mode MODE` declaration against
OBSERVED write-capable effects in its own `code=`-bound python files
(v0, python-only, disclosed cut -- module docstring).

Per-mode semantics implemented and litmus-tested (10 unit tests, all
passing, `tests/unit/strata/test_mode_conformance.py`):
- READ: any write-capable observation (open() in w/x/+ mode,
  os.remove/rename/unlink, shutil.rmtree/move, pathlib
  write_text/write_bytes/.unlink(, socket .send/.sendall/sendto, or a
  DML keyword on a .execute( line) fires, naming file:line.
- APPEND: same write-capable set fires EXCEPT append-mode opens
  (open(path, "a"...)).
- EXCLUSIVE / ALPHA: require a code-checkable `lock` arbiter (v0 only
  supports the `lock "NAME"` ResourceDecl form, not `arbitrated_by NODE`
  -- disclosed cut); every write-capable observation must sit inside a
  `with` block naming that lock (indentation-based block scan,
  `_enclosing_with_headers`) or it fires "outside the arbiter context".
  A resource with no code-checkable lock fails closed even with zero
  observations.
- WRITE: unrestricted in v0 (path-level "only on declared paths" needs
  identity this pass does not have -- disclosed cut, follow-up filed).

Findings on frob's own strata model (design/frob.strata): every real
`access` declaration in the repo's own design is `mode write` (the
tickets_ledger resource, guarded by `lock "tickets.lock"` per T-0956) --
run against the real `src/frob/` tree with a merged `Module.resources`
(ad hoc script, not committed), `check_mode_conformance` reports ZERO
SYS205 violations, consistent with WRITE mode's v0 baseline. There is
currently no `read`/`append`/`alpha`/`exclusive` declaration anywhere in
frob's own design for this new check to non-trivially exercise yet --
itself a disclosed finding, not a defect: SYS205 has real work to do only
once a node adopts one of the four restricted modes.

DELIBERATELY NOT WIRED IN THIS PASS (disclosed cut, mirrors T-0700's own
precedent): CLI dispatch (`frob sys audit`, `src/frob/app/sys_runner.py`)
and the T-0174 waiver channel are out of T-0701's declared scope --
`check_mode_conformance` is a pure, fully-tested function; wiring it and
adding a docs/strata/host.md section is filed as T-1061.
Three further v0 detection cuts (ALPHA upgrade-deadlock anti-pattern,
`arbitrated_by`-arbiter code-identity, WRITE path-scoping) are filed as
T-1060.

### Changed
```
 src/frob/strata/__init__.py                |  12 +
 src/frob/strata/_mode_conformance.py       | 488 +++++++++++++++++++++++++++++
 tests/unit/strata/test_mode_conformance.py | 233 ++++++++++++++
 3 files changed, 733 insertions(+)
```

### Evidence
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_read_mode_fails_on_a_write_open` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_read_mode_discharges_on_read_only_code` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_append_mode_fails_on_a_truncating_write` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_append_mode_discharges_on_an_append_only_open` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_exclusive_mode_fails_on_access_outside_the_arbiter` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_exclusive_mode_discharges_inside_the_declared_lock` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_exclusive_mode_with_no_lock_declared_fails_closed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_alpha_mode_fails_on_an_unguarded_write` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_write_mode_is_unrestricted_in_v0` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_mode_conformance.py::TestCheckModeConformance::test_node_with_no_access_declarations_is_never_checked` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 1 error(s), 3099 warning(s), 377 waived
- error-findings: AFFECT001@src/frob/strata/_mode_conformance.py

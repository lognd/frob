## Done report

Migrated design/frob.strata off the deprecated fs/fs-read capability
spellings onto the T-0717 mode-qualified fs.write/fs.read spellings:
mechanical replace of every `may "fs";` -> `may "fs.write";` (15 blocks)
and `may "fs-read";` -> `may "fs.read";` (13 blocks), since every block
in this file used bare fs to denote the write-derived observation and
already declared fs-read separately wherever it also read (no
read-half ever dropped). Updated every stale comment that explained the
old fs/fs-read scanner-fold convention (cli, registry_model, fleet,
core/clean, mutate, natives, serve, deploy, tickets_ledger, testsuite,
scripts_ops, stratamod headers).

Discovered mid-work: THREAT002's DEFAULT_BENIGN_CAPABILITIES catalog
in src/frob/strata/_threat.py only excused the deprecated bare
fs/fs-read kinds, not the new fs.write/fs.read spellings, so the
migration failed closed (SYS gate DOC003/THREAT002 errors on every
migrated node) until two new BenignCapability entries were added
(kind="fs.write", kind="fs.read"), mirroring the existing
net/net.connect/net.listen precedent. Scope was formally widened via
`frob ticket scope --add` to cover this file plus its test
(tests/unit/strata/test_threat.py), which needed its exhaustiveness
lock count bumped 13 -> 15 to match.

litmus/deprecated-alias-path tests (tests/unit/strata/test_effects.py,
test_selfconform.py, test_waive.py, test_infra.py,
test_store_code_may.py, test_elaborate.py) deliberately still declare
the bare fs/fs-read spellings as Python fixtures to exercise the
deprecated-alias normalization path itself -- left untouched, all still
pass unchanged.

No litmus .strata files (tests/unit/strata/litmus/*.strata) exist in
this repo; the only .strata file with fs/fs-read declarations was
design/frob.strata.

### Changed
```
 tickets.md | 67 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 67 insertions(+)
```

### Evidence
- `tests/unit/strata/test_threat.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_has_a_substantive_caught_by` (pytest node id, verified passing when recorded)
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 400 warning(s), 687 waived
- error-findings: none (measured, zero errors)

## Done report

H-1/F-273: a browser node declaring no `carries()` facts at all has
nothing for the PII gate to compare a client-side storage write
against, so a PII leak into `localStorage` is invisible. `attr no_pii;`
is the explicit "this node carries no personal data" declaration; any
client-storage write on such a node is then a contradiction with no
automatic way to resolve it (no taint analysis), so it is deny-by-
default and demands a reasoned per-call-site `frob:waive PII013
reason="..."` -- the cheap, purely structural first step per the
ticket's own explicit ranking over taint/dataflow analysis.

### Changed
```
 src/frob/gates/_pii_structural/__init__.py | 191 ++++++++++++++++++++++++++++-
 tests/test_pii_structural_gate.py          | 133 ++++++++++++++++++++
 tickets/T-4073/done-report.md              |  27 ++++
 tickets/T-4073/ticket.md                   |  22 +++-
 4 files changed, 366 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_fires_on_namespaced_session_storage_write` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_stays_quiet_without_no_pii_declaration` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_stays_quiet_on_unrelated_setitem_call` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_no_scan_without_any_no_pii_node` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_waived_call_site_is_accepted` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestClientStorageNoPii::test_fires_on_local_storage_write` (pytest node id, verified passing when recorded)

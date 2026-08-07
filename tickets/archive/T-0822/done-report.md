## Done report

Changed:
src/frob/vet/_registry.py::_result_from_network
src/frob/vet/_nvd.py::_fetch_from_network
design/frob.strata (vet node: attr flag=frob_vet_net_kill_switch; replaces waive "LINT004")
tests/test_vet.py::TestRegistryLookup.test_fetch_publish_date_refuses_when_net_disabled
tests/test_vet.py::TestNvdLookup.test_fetch_cwe_for_cve_refuses_when_net_disabled

Evidence:
tests/test_vet.py::TestRegistryLookup::test_fetch_publish_date_refuses_when_net_disabled
tests/test_vet.py::TestNvdLookup::test_fetch_cwe_for_cve_refuses_when_net_disabled
uv run --frozen pytest tests/test_vet.py -q -> 145 passed
uv run --frozen frob test --base main -> [PASS] python exit=0 12.64s (touched-set incl. both new tests + frob self-model sys-gate tests)
uv run --frozen frob sys audit -> "sys audit: PROVED -- zero gaps across every configured view" (zero LINT004 waivers left anywhere in the model, vet's included)

Filed: none (T-0822 is this ticket itself, filed because dispatch id T-0817 does not exist in the ledger -- see deviations below)

Gates: frob check --only {lint,static,gates-fast,gates-native,gates-security} --ticket T-0822 all clean (0 errors); the one pre-existing lint red (tests/system/test_cli_doctor.py ty diagnostic, predates this change, outside scope) is untouched.

### Changed
```
 design/frob.strata        | 23 ++++++++++-------
 src/frob/vet/_nvd.py      | 14 ++++++++++
 src/frob/vet/_registry.py | 17 +++++++++++++
 tests/test_vet.py         | 65 +++++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                | 58 ++++++++++++++++++++++++++++++++++++++++++
 5 files changed, 168 insertions(+), 9 deletions(-)
```

### Evidence
(no evidence recorded)

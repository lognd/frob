## Done report

REL201 anchored its proof-against-code check on flow.src only, making the
repo's one real network flow (f_registry_fetch: registry -> vet) forever
uncheckable-silent -- registry is foreign/codeless, while vet (the real
caller) has genuinely provable code (src/frob/vet/_nvd.py:163,
urllib.request.urlopen(url, timeout=timeout_s)).

Fix: `_unproven_timeout_violations` now collects both flow endpoints
(src, dst), keeps only those with bound code (`_bound_endpoints`), and
treats the flow as PROVED if ANY bound endpoint's code carries a real
`timeout=`-shaped token (an OR across endpoints, not just src). A flow
where neither endpoint has bound code stays uncheckable-silent
(unchanged). REL200 untouched.

Added two litmus-style unit tests exercising the exact codeless-src/
coded-dst shape: one where dst's code proves the timeout (must not
fire), one where dst's code lacks the token (must fire, reporting node
= dst, the only checkable endpoint).

Verified `uv run frob sys audit` no longer reports any REL201 finding
for f_registry_fetch (proved silently, i.e. no violation/waiver line
for it), where before this fix it would have been silently uncheckable
for the wrong reason (src has no code) rather than genuinely proved
(dst does, and its code has timeout=).

### Changed
```
 src/frob/strata/_reliability.py       | 76 ++++++++++++++++++++++----------
 tests/unit/strata/test_reliability.py | 63 +++++++++++++++++++++++++++
 tickets.md                            | 82 +++++++++++++++++++++++++++++++++--
 3 files changed, 194 insertions(+), 27 deletions(-)
```

### Evidence
- `tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_codeless_src_with_coded_dst_proves_against_dst` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_codeless_src_with_coded_dst_lacking_evidence_fires_against_dst` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_reliability.py::TestUnprovenTimeout::test_declared_timeout_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)

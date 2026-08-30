## Done report

Decision: legitimate self-reference, not a portability bug. No code
behavior change -- documented the reasoning in place at
`_NON_LANGUAGE_FINGERPRINT_PACKAGES`'s definition.

Reasoning: this cache belongs to frob's OWN analyzer, not to the repo it
is scanning. The fingerprint exists to answer "would a version bump of a
package that determines this cache's PARSE OUTPUT silently make the
cache stale" (the T-0243 malmberg incident this mechanism was built to
prevent). The packages that determine THIS cache's parse output are
always frob's own extraction/digest code and strata-core's native
`.strata` grammar, regardless of which host repo is under analysis -- a
consumer repo's own declared dependencies play no part in how
`frob.graph` parses that repo's source. Unlike PORT001-PATH's silent-
pass/false-fire class (where a hardcoded path segment really can break on
a differently-laid-out host repo), retargeting this tuple to a config-
driven lookup would not fix a cross-repo bug; it would just replace two
names that are correct for every host repo with a lookup that could
return the wrong ones. This matches PORT001-IDENT's own documented
posture (`_port_selfcheck.py`'s `_port001_ident_violation` docstring):
most real PORT001-IDENT hits are legitimate self-reference and "no action
is required" once reviewed -- `_ALLOWLIST` entries there are for gate-
internal detector files; this ticket's scope is `src/frob/graph/cache.py`
only, so the decision is recorded as an in-place comment rather than
touching the out-of-scope gate module (that allowlist mechanism is
T-3435's adjacent scope, a different unrelated PORT001 gap).

Evidence: no behavior change; existing coverage re-run to confirm no
regression:
- tests/test_graph.py::TestBuildIncremental (fingerprint invalidation
  tests, including the frob:waive-documented `_NON_LANGUAGE_FINGERPRINT_PACKAGES`
  tuple-shape assertion)
- tests/unit/test_dup_cache.py
24/24 pass under -p no:xdist.

### Changed
```
 tickets/T-3433/ticket.md | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_graph.py::TestBuildIncremental::test_fingerprint_bump_rebuilds` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 14 error(s), 4024 warning(s), 855 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DOC007@tests/unit/test_main_entry.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, DRIFT002@tests/unit/test_main_entry.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3433, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
